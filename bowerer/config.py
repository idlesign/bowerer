"""Exposes functions to work with Bower configuration - bowerrc."""
import json
import pwd
import tempfile
from os import environ as env, path, getuid, getcwd

from six import string_types, iteritems

from .utils import get_user_agent

try:
    from functools import reduce
except ImportError:
    pass  # Py 2

USERNAME = pwd.getpwuid(getuid())[0]

DIR_CURRENT = getcwd()
DIR_HOME = path.expanduser('~')
DIR_TMP = path.join(tempfile.gettempdir(), USERNAME)
DIR_BASE = path.abspath(DIR_HOME or DIR_TMP)

PROXY = env.get('HTTP_PROXY')
PROXY_HTTPS = env.get('HTTPS_PROXY', PROXY)


PATHS = {
    'config': env.get('XDG_CONFIG_HOME') or path.join(DIR_BASE, '.config/bower'),
    'data': env.get('XDG_DATA_HOME') or path.join(DIR_BASE, '.local/share/bower'),
    'cache': env.get('XDG_CACHE_HOME') or path.join(DIR_BASE, '.cache/bower'),
    'tmp': DIR_TMP
}


DEFAULTS = {
    'color': True,
    'interactive': None,

    'strict-ssl': True,
    'user-agent': get_user_agent(PROXY or PROXY_HTTPS),
    'registry': 'https://bower.herokuapp.com',
    'shorthand-resolver': 'git://github.com/{{owner}}/{{package}}.git',
    'timeout': 30000,
    'proxy': PROXY,
    'https-proxy': PROXY_HTTPS,
    'ca': {'search': []},

    'cwd': DIR_CURRENT,
    'directory': 'bower_components',
    'tmp': PATHS['tmp'],
    'storage': {
        'packages': path.join(PATHS['cache'], 'packages'),
        'links': path.join(PATHS['data'], 'links'),
        'completion': path.join(PATHS['data'], 'completion'),
        'registry': path.join(PATHS['cache'], 'registry'),
        'empty': path.join(PATHS['data'], 'empty')  # Empty dir, used in GIT_TEMPLATE_DIR among others
    }
}


_NOT_SET = object()


def merge(base, updater):
    """Merges two configuration dictionaries updating one with values
    from another.

    :param dict base:
    :param dict updater:
    :rtype: dict
    """

    if isinstance(base, dict):
        for key_base, val_base in iteritems(base):
            val_updater = updater.get(key_base, _NOT_SET)
            if val_updater is _NOT_SET:
                continue

            if isinstance(val_base, list):
                val_base.extend(set(val_updater).difference(val_base))
                updater[key_base] = val_base

            elif isinstance(val_base, dict):
                updater[key_base] = merge(val_base, val_updater)

        base.update(updater)

    return base


def normalize(conf):
    """Normalizes a given configuration dictionary.

    :param dict conf:
    :rtype: dict
    """

    def expand(section_name):
        section = conf.get(section_name)
        if isinstance(section, string_types):
            conf[section_name] = {
                'search': [section],
                'register': section,
                'publish': section
            }
        elif section:
            search = section.get('search')
            if search and not isinstance(search, list):
                section['search'] = [search]

    expand('registry')
    expand('ca')

    registry = conf.get('registry')
    registry['search'] = map(lambda item: item.rstrip('/'), registry.get('search', []))
    registry['register'] = registry.get('register', '').rstrip('/')
    registry['publish'] = registry.get('publish', '').rstrip('/')

    conf['tmp'] = path.abspath(conf['tmp'])
    return conf


def read_json(filepath):
    """Tries to read JSON from a given location.
    Returns empty dictionary if fails.

    :param filepath:
    :rtype: dict
    """
    contents = {}
    try:
        with open(filepath) as f:
            contents = json.load(f)

    except Exception:
        pass

    return contents


def load(config=None):
    """Loads and returns configuration comprised from data stored
    in various locations.

    :param dict config:
    :rtype: dict
    """

    config = config or {}

    name_base = 'bower'
    name_rc = name_base + 'rc'

    sources = [
        DEFAULTS,
        {'cwd': DIR_CURRENT},
        read_json(path.join('/etc', name_rc)),
        read_json(path.join(DIR_HOME, '.' + name_rc) if DIR_CURRENT != DIR_HOME else {}),
        read_json(path.join(PATHS['config'], name_rc)),
        read_json(path.join(DIR_CURRENT, '.' + name_rc)),  # todo find upwards from parents
        # env('npm_package_config_' + name + '_'),
        # env(name + '_'),
        config
    ]
    result = normalize(reduce(merge, sources))
    return result


def parse_from_command_line(args):
    """Parses config data from command line arguments and returns it as a dict,
    e.g --config.endpoint-parser=<parser> --config.storage.cache=<cache>

    :param list args:
    :rtype: dict
    """
    config = {}

    for arg in args:
        if arg.startswith('--config'):
            key = arg.replace('--config.', '')
            key, value = key.split('=')
            value = value.strip()
            if '.' in key:
                key = key.split('.')
                value = {key[1].strip(): value}
                key = key[0]

            if value == 'false':
                value = False

            merge(config, {key.strip(): value})

    return config
