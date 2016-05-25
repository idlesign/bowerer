from collections import OrderedDict

from semantic_version import Version

from .settings import LOGGER
from .utils import get_json


class Host(object):

    def __init__(self, url):
        self.url = url


class GitHub(Host):

    TITLE = 'GitHub'
    BASE_URL = 'https://api.github.com'
    RAW_URL = 'https://raw.githubusercontent.com'

    @classmethod
    def can_handle(cls, url):
        return url.startswith('git')

    def get_versions(self):

        repo_owner, repo_name = self.url.rstrip('.git').rsplit('/', 2)[-2:]
        repo_ident = '%s/%s' % (repo_owner, repo_name)
        url = '%s/repos/%s/tags' % (self.BASE_URL, repo_ident)

        LOGGER.debug('Getting version list from %s ...', url)

        versions = OrderedDict()
        for version_data in get_json(url):
            version_name = version_data['name']
            version_num = Version.coerce(version_name.lstrip('v'), partial=True)
            versions[version_num] = {
                'name': version_name,
                'url_pack': version_data['tarball_url'],
                'url_root': '%s/%s/%s' % (self.RAW_URL, repo_ident, version_name),
            }

        return versions
