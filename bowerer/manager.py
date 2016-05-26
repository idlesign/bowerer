from os.path import join
from functools import cmp_to_key

from semantic_version import compare as v_compare, match as v_match

try:
    from itertools import ifilter as filter
except ImportError:
    pass


class Manager(object):

    def __init__(self, config):
        self.config = config
        self.configure({})
        self._targets = []
        self._resolved = {}
        self._installed = {}
        self._incompatibles = {}
        self._conflicted = {}
        self._resolutions = {}
        self._force_latest = False

    def configure(self, setup):
        targets_hash = {}
        self._targets = setup.get('targets') or []

        for target in self._targets:
            target['initialName'] = target['name']
            target['dependants '] = target.get('dependants ', {}).values()
            targets_hash[target['name']] = True

            # If the endpoint is marked as newly, make it unresolvable
            target['unresolvable'] = target.get('newly', False)

        self._resolved = {}
        self._installed = {}

        for name, meta in setup.get('resolved', {}).items():
            meta['dependants'] = meta.get('dependants', {}).values()
            self._resolved[name] = [meta]
            self._installed[name] = meta['pkgMeta']

        self._installed.update(setup.get('installed', {}))

        self._incompatibles = {}
        setup['incompatibles'] = self._make_unique(setup.get('incompatibles', [])) or []

        for endpoint in setup['incompatibles']:
            name = endpoint['name']
            self._incompatibles[name] = self._incompatibles.get(name) or []
            self._incompatibles[name].append(endpoint)

            endpoint['dependants'] = endpoint.get('dependants', {}).values()

            # Mark as conflicted so that the resolution is not removed
            self._conflicted[name] = True

            # If not a target/resolved, add as target
            if not targets_hash.get(name) and not self._resolved.get(name):
                self._targets.append(endpoint)

        self._resolutions = setup.get('resolutions') or {}
        self._targets = self._make_unique(self._targets)
        self._force_latest = setup.get('force_latest', False)

    def resolve(self):

        if not self._targets:
            self._dissect()
        else:
            map(self._fetch, self._targets)

    def _dissect(self):

        suitables = {}

        def version_compare(first, second):
            result = v_compare(first['pkgMeta']['version'], second['pkgMeta']['version'])
            result = {-1: 1, 0: 0, 1: -1}.get(result)

            if not result:
                if first['target'] == '*':
                    return 1

                if second['target'] == '*':
                    return -1

            return result

        for name, endpoints in self._resolved.items():
            semvers = [endpoint for endpoint in endpoints if endpoint['pkgMeta'].get('version')]
            semvers = sorted(semvers, key=cmp_to_key(version_compare))

            for endpoint in semvers:
                if endpoint.get('newly')and endpoint['target'] == '*' and not endpoint.get('untargetable'):
                    endpoint['target'] = '~' + endpoint['pkgMeta']['version']
                    endpoint['originalTarget'] = '*'

            non_semvers = [endpoint for endpoint in endpoints if not endpoint['pkgMeta'].get('version')]

            suitables[name] = self._elect_suitable(name, semvers, non_semvers)

    def _fetch(self, target):
        a = 1

    def _elect_suitable(self, name, semvers, non_semvers):

        picks = []

        if semvers and non_semvers:
            picks.extend(semvers)
            picks.extend(non_semvers)

        elif non_semvers:
            if len(non_semvers) == 1:
                return non_semvers[0]

            picks.extend(non_semvers)

        else:
            suitable = None
            for subject in semvers:
                for loop_endpoint in semvers:
                    if subject == loop_endpoint or v_match(subject['pkgMeta']['version'], loop_endpoint['target']):
                        suitable = subject
                        break

            if suitable:
                return suitable

            picks.extend(semvers)

        # At this point, there's a conflict
        self._conflicted[name] = True

        # Prepare data to be sent bellow
        # 1 - Sort picks by version/release
        def compare_picks(pick1, pick2):
            version1 = pick1['pkgMeta']['version']
            version2 = pick2['pkgMeta']['version']

            if version1 and version2:
                result = v_compare(version1, version2)
                if result:
                    return result
            else:
                if version1:
                    return 1
                if version2:
                    return -1

            if len(pick1['dependants']) > len(pick2['dependants']):
                return -1

            if len(pick1['dependants']) < len(pick2['dependants']):
                return -1

            return 0

        picks = sorted(picks, key=cmp_to_key(compare_picks))

        # 2 - Transform data
        data_picks = []
        for pick in picks:
            data_pick = self.to_data(pick)
            data_pick['dependants'] = map(self.to_data, pick['dependants'])
            data_pick['dependants'] = sorted(data_pick['dependants'], key=lambda dep: dep['endpoint']['name'])
            data_picks.append(data_pick)

        # Check if there's a resolution that resolves the conflict
        # Note that if one of them is marked as unresolvable,
        # the resolution has no effect
        resolution = self._resolutions.get(name)
        unresolvable = None
        for pick in picks:
            if pick.get('unresolvable'):
                unresolvable = pick
                break

        if resolution and not unresolvable:
            suitable = -1

        # TODO implement


    def preinstall(self, json_dict):
        components_dir = join(self.config['cwd'], self.config['directory'])

        # TODO implement

    def _make_unique(self, endpoints):

        len_endpoints = len(endpoints)

        def func_filter(endpoint_tuple):
            idx, endpoint = endpoint_tuple

            for idx_loop in range(idx, len_endpoints):
                current = endpoints[idx_loop]
                if current == endpoint:
                    return False

                current_name = current.get('name')
                looped_name = endpoint.get('name')

                if not current_name and not looped_name:
                    if current.get('source') != endpoint.get('source'):
                        continue

                elif current_name != looped_name:
                    continue

                if current.get('target') != endpoint.get('target'):
                    return False

            return True

        filtered = filter(func_filter, [(idx, endpoint) for idx, endpoint in enumerate(endpoints)])
        return list(filtered)  # todo
