import json
from collections import deque
from hashlib import md5
from os.path import basename, join, islink, isdir
from os import walk, listdir

from .utils import read_json, JsonReader, Endpoint
from .settings import LOGGER
from .exceptions import ProjectError
from .manager import Manager


class Project(object):

    def __init__(self, config):
        self.config = config
        self.options = {}
        self.json = {}
        self.json_filepath = None
        self.cache_installed = None
        self.manager = Manager(config)

    def install(self, endpoints, options=None, config=None):
        self.config = config or {}
        self.options = options or {}

        project_json, project_tree, _ = self.analyse()
        if not self.json_filepath and not len(endpoints):
            raise ProjectError('No bower.json present')

        incompatibles = []
        targets = []
        resolved = {}

        def walker_func(node, name):
            if node.get('incompatible'):
                incompatibles.append(node)
            elif node.get('missing') or node.get('different') or self.config.get('force'):
                targets.append(node)
            else:
                resolved[name] = node

        # Recover tree
        self.walk_tree(project_tree, walker_func, once=True)

        endpoints = endpoints or []
        for endpoint in endpoints:
            endpoint['newly'] = True
            targets.append(endpoint)

        self._bootstrap(targets, resolved, incompatibles)

        self.manager.preinstall(self.json)

    def _bootstrap(self, targets, resolved, incompatibles):
        installed = {name: meta['pkgMeta'] for name, meta in self.cache_installed.items()}  # todo mout.object.map was used

        self.json['resolutions'] = self.json.get('resolutions') or {}

        self.manager.configure({
            'targets': targets,
            'resolved': resolved,
            'incompatibles': incompatibles,
            'resolutions': self.json['resolutions'],
            'installed': installed,
            'force_latest': self.options['force_latest']
        })
        self.manager.resolve()

        if not self.json['resolutions']:
            del self.json['resolutions']

    def walk_tree(self, node, func, once=True):
        queue = deque(node['dependencies'].values())

        if once:
            once = []

        def filter_dep(dep):
            matched = False
            for stacked in once:
                if matched:
                    break

                if dep['endpoint']:
                    matched = (dep['endpoint'] == stacked['endpoint'])
                    continue

                matched = (
                    dep['name'] == stacked['name'] and
                    dep['source'] == stacked['source'] and
                    dep['target'] == stacked['target'])

            return not matched

        while queue:
            node = queue.popleft()
            result = func(node, node['endpoint']['name'] if node.get('endpoint') else node['name'])

            if result == False:
                continue

            dependencies = node['dependencies'].values()[:]

            if once:
                dependencies = [dep for dep in dependencies if filter_dep(dep)]
                once.extend(dependencies)

            queue.extendleft(dependencies)

    def analyse(self):
        project_json = self.read_json()
        installed_flat = dict(self.gather_installed())
        links = self.gather_installed_links()

        json_copy = dict(project_json)

        cwd = self.config['cwd']
        project_tree = {
            'name': project_json['name'],
            'source': cwd,
            'target': project_json.get('version') or '*',
            'pkgMeta': json_copy,
            'canonicalDir': cwd,
            'root': True
        }

        json_copy['dependencies'] = json_copy.get('dependencies') or {}
        json_copy['devDependencies'] = json_copy.get('devDependencies') or {}

        installed_flat.update(links)
        for name, meta in installed_flat.items():
            pkg_meta = meta['pkgMeta']
            is_saved = json_copy['dependencies'].get(name) or json_copy['devDependencies'].get(name)

            # _direct property is saved by a manager when .newly is specified
            # if package is uninstalled pkgMeta may be undefined
            if not is_saved and pkg_meta and pkg_meta.get('_direct'):
                meta['extraneous'] = True
                if meta.get('linked'):
                    json_copy['dependencies'][name] = pkg_meta.get('version') or '*'
                else:
                    json_copy['dependencies'][name] = (
                        (pkg_meta.get('_originalSource', '') or pkg_meta.get('_source', '')) +
                        '#' + pkg_meta.get('_target'))

        # Restore dependency tree for main deps.
        self._restore_refs(project_tree, installed_flat, 'dependencies')

        if not self.options['production']:
            # Restore dependency tree for dev deps.
            self._restore_refs(project_tree, installed_flat, 'devDependencies')

        for name, meta in installed_flat.items():
            # Restore dependency tree for extra deps.
            if not meta.get('dependants'):
                meta['extraneous'] = True
                self._restore_refs(meta, installed_flat, 'dependencies')
                project_tree['dependencies'][name] = meta

        try:
            del installed_flat[project_json['name']]
        except KeyError:
            pass

        return project_json, project_tree, installed_flat

    @classmethod
    def _restore_refs(cls, node, flat, json_key, processed=None):

        if node.get('missing', False):
            return

        node['dependencies'] = node.get('dependencies') or {}
        node['dependants'] = node.get('dependants') or {}
        processed = processed or {}

        deps = {
            k: v for k, v in node['pkgMeta'].get(json_key, {}).items()
            if not processed.get(node['name'] + ':' + k)}

        for dep_ident, dep_descr in deps.items():
            local = flat[dep_ident]
            decomposed = Endpoint.decompose_from_json(dep_ident, dep_descr)
            restored = None
            compatible = None
            original_source = None

            if not local:
                # Check dep is not installed.
                flat[dep_ident] = restored = decomposed
                restored['missing'] = True
            else:
                # Even if it is installed, check if it's compatible
                # Note that linked packages are interpreted as compatible
                # This might change in the future: #673
                compatible = (
                    local.get('linked') or
                    (not local.get('missing') and
                     decomposed['target'] == local['pkgMeta']['_target']))

                if not compatible:
                    restored = decomposed

                    if not local.get('missing'):
                        restored['pkgMeta'] = local['pkgMeta']
                        restored['canonicalDir'] = local['canonicalDir']
                        restored['incompatible'] = True
                    else:
                        restored['missing'] = True

                else:
                    restored = local
                    local.update(decomposed)  # todo recursive update?

                # Check if source changed, marking as different if it did
                # We only do this for direct root dependencies that are compatible
                if node['root'] and compatible:
                    original_source = local.get('pkgMeta', {}).get('_originalSource')
                    if original_source and original_source != decomposed['source']:
                        restored['different'] = True

            # Cross reference
            node['dependencies'][dep_ident] = restored
            processed[node['name'] + ':' + dep_ident] = True

            restored['dependants'] = restored.get('dependants', {})

            # We need to clone due to shared objects in the manager!
            restored['dependants'][node['name']] = dict(node)

            # Call restore for this dependency
            cls._restore_refs(restored, flat, 'dependencies', processed)

            # Do the same for the incompatible local package
            if local and restored != local:
                cls._restore_refs(local, flat, 'dependencies', processed)

    def read_json(self):
        cwd = self.config['cwd']
        contents, deprecated, is_dummy = read_json(cwd, dummy_json={'name': basename(cwd) or 'root' })
        self.json = contents

        if deprecated:
            LOGGER.warning('Deprecated file is used: %s', deprecated)

        if not is_dummy:
            self.json_filepath = join(cwd, deprecated or JsonReader.filename_modern)

        json_str = json.dumps(contents, indent=2) + '\n'
        self.json_hash = md5(json_str).hexdigest()
        return contents

    def gather_installed(self):
        components_path = join(self.config['cwd'], self.config['directory'])

        endpoints = {}

        expected_filename = JsonReader.filename_modern_hidden
        for current_dir, _, files in walk(components_path):
            if expected_filename in files:
                filepath = join(current_dir, expected_filename)
                name = basename(current_dir)
                pkg_meta, _, _ = read_json(filepath)
                endpoints[name] = {
                    'name': name,
                    'source': pkg_meta.get('_originalSource') or pkg_meta['_source'],
                    'target': pkg_meta['_target'],
                    'canonicalDir': current_dir,
                    'pkgMeta': pkg_meta
                }

        self.cache_installed = endpoints
        return endpoints

    def gather_installed_links(self):
        components_path = join(self.config['cwd'], self.config['directory'])

        endpoints = {}

        for directory in listdir(components_path):
            fullpath = join(components_path, directory)

            if not (isdir(fullpath) and islink(fullpath)):
                continue

            pkg_meta, deprecated, _ = read_json(fullpath, dummy_json={'name': directory})
            pkg_meta['_direct'] = True
            endpoints[directory] = {
                'name': directory,
                'source': fullpath,
                'target': '*',
                'canonicalDir': fullpath,
                'pkgMeta': pkg_meta,
                'linked': True
            }
        return endpoints
