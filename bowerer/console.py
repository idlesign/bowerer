import sys
import argparse

from bowerer.config import parse_from_command_line
from bowerer.api import *


def main():
    from bowerer import VERSION

    version_str = '.'.join(map(str, VERSION) )

    main_parser = argparse.ArgumentParser(prog='bowerer', description='Bower for pythoneers.')

    main_parser.add_argument('--version', action='version', version=version_str)
    main_parser.add_argument('--force', '-f', action='store_true', default=False,
                             help='Makes various commands more forceful')
    main_parser.add_argument('--json', '-j', action='store_true', default=False,
                             help='Output consumable JSON')
    main_parser.add_argument('--log-level', '-l', help='What level of logs to report')
    main_parser.add_argument('--offline', '-o', action='store_true', default=False,
                             help='Do not hit the network')
    main_parser.add_argument('--quiet', '-q', action='store_true', default=False,
                             help='Only output important information')
    main_parser.add_argument('--silent', '-s', action='store_true', default=False,
                             help='Do not output anything, besides errors')
    main_parser.add_argument('--verbose', '-V', action='store_true', default=False,
                             help='Makes output more verbose')
    main_parser.add_argument('--allow-root', action='store_true', default=False
                             , help='Allows running commands as root')
    main_parser.add_argument('--no-color', action='store_true', default=False,
                             help='Disable colors')

    main_subparsers = main_parser.add_subparsers(dest='main_subparsers')

    p = main_subparsers.add_parser

    p_cache = p('cache', help='Manage bower cache.')
    cache_subparsers = p_cache.add_subparsers(dest='cache_subparsers')

    p_cache_clean = cache_subparsers.add_parser('clean', help='Cleans cached packages.')
    p_cache_clean.add_argument('package', help='<package> or <package>#<version>', nargs='*')
    p_cache_list = cache_subparsers.add_parser('list', help='Lists cached packages.')
    p_cache_list.add_argument('package', nargs='*')

    p_home = p('home',
               help='Opens a package homepage into your favorite browser.\n\n'
                    'If no <package> is passed, opens the homepage of the local package.')
    p_home.add_argument('package', help='<package> or <package>#<version>')

    p_info = p('info', help='Displays overall information of a package or of a particular version.')
    p_info.add_argument('package', help='<package> or <package>#<version>')
    p_info.add_argument('--property')

    p('init', help='Creates a bower.json file based on answers to questions.')

    # i
    p_install = p('install', help='Installs the project dependencies or a specific set of endpoints.')
    p_install.add_argument('endpoint', help='Endpoints can have multiple forms:\n'
                                            '- <source>\n'
                                            '- <source>#<target>\n'
                                            '- <name>=<source>#<target>\n\n'
                                            'Where:\n'
                                            '- <source> is a package URL, physical location or registry name\n'
                                            '- <target> is a valid range, commit, branch, etc.\n'
                                            '- <name> is the name it should have locally.', nargs='+')
    p_install.add_argument('--force-latest', '-F', action='store_true', default=False,
                           help='Force latest version on conflict')
    p_install.add_argument('--production', '-p', action='store_true', default=False,
                           help='Do not install project devDependencies')
    p_install.add_argument('--save', '-S', action='store_true', default=False,
                           help='Save installed packages into the project\'s bower.json dependencies')
    p_install.add_argument('--save-dev', '-D', action='store_true', default=False,
                           help='Save installed packages into the project\'s bower.json devDependencies')
    p_install.add_argument('--save-exact', '-E', action='store_true', default=False,
                           help='Configure installed packages with an exact version rather than semver')

    p_link = p('link',
               help='The link functionality allows developers to easily test their packages.\n'
                    'Linking is a two-step process.\n\n'
                    'Using \'bower link\' in a project folder will create a global link.\n'
                    'Then, in some other package, \'bower link <name>\' will create a link '
                    'in the components folder pointing to the previously created link.\n\n'
                    'This allows to easily test a package because changes will be reflected immediately.\n'
                    'When the link is no longer necessary, simply remove it with \'bower uninstall <name>\'.')
    p_link.add_argument('name')
    p_link.add_argument('--local_name')

    # ls
    p_list = p('list', help='List local packages - and possible updates.')
    p_list.add_argument('--paths', '-p', help='Generates a simple JSON source mapping')
    p_list.add_argument('--relative', '-r',
                        help='Make paths relative to the directory config property, which defaults to bower_components')

    p_login = p('login', help='Authenticate with GitHub and store credentials to be used later.')
    p_login.add_argument('--token', '-t',
                         help='Pass an existing GitHub auth token rather than prompting for username and password.')

    p_lookup = p('lookup', help='Looks up a package URL by name.')
    p_lookup.add_argument('name')

    p('prune', help='Uninstalls local extraneous packages.')

    p_register = p('register', help='Registers a package.')
    p_register.add_argument('name')
    p_register.add_argument('url')

    p_search = p('search', help='Finds all packages or a specific package.')
    p_search.add_argument('name')

    p_update = p('update', help='Updates installed packages to their newest version according to bower.json.')
    p_update.add_argument('name', nargs='+')
    p_update.add_argument('--force-latest', '-F', help='Force latest version on conflict')
    p_update.add_argument('--production', '-p', help='Do not install project devDependencies')

    # rm, unlink
    p_uninstall = p('uninstall', help='Uninstalls a package locally from your bower_components directory')
    p_uninstall.add_argument('name', nargs='+')
    p_uninstall.add_argument('--save', '-S',
                             help='Remove uninstalled packages from the project\'s bower.json dependencies')
    p_uninstall.add_argument('--save-dev', '-D',
                             help='Remove uninstalled packages from the project\'s bower.json devDependencies')

    p_unregister = p('unregister', help='Unregisters a package.')
    p_unregister.add_argument('name')

    #todo [<newversion> | major | minor | patch]
    p_version = p('version',
                  help='Run this in a package directory to bump the version and write the new data back ')
                       # 'to the bower.json file.\n\n'
                       # 'The newversion argument should be a valid semver string, or a valid second argument '
                       # 'to semver.inc (one of "build", "patch", "minor", or "major"). In the second case, '
                       # 'the existing version will be incremented\nby 1 in the specified field.\n\n'
                       # 'If run in a git repo, it will also create a version commit and tag, and fail '
                       # 'if the repo is not clean.\n\n'
                       # 'If supplied with --message (shorthand: -m) config option, bower will use it as '
                       # 'a commit message when creating a version commit. If the message config contains %s then '
                       # 'that will be replaced with the resulting\n'
                       # 'version number. For example:\n\n    '
                       # 'bower version patch -m "Upgrade to %s for reasons"')
    p_version.add_argument('--message', '-m', help='Custom git commit and tag message')

    parsed_args = main_parser.parse_known_args()
    other_args = parsed_args[1]
    parsed_args = vars(parsed_args[0])  # Convert known args to dict
    parsed_args['config'] = parse_from_command_line(other_args)

    target_func_name = parsed_args['main_subparsers']
    del parsed_args['main_subparsers']
    target_func = globals()[target_func_name]
    target_func(**parsed_args)


main()
