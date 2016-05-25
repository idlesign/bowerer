import re
import json
from os.path import basename, isdir, abspath, join, exists

import requests
from six import string_types

from .exceptions import EndpointError, JsonError
from .settings import LOGGER


def get_json(url, allow_empty=False):
    """Returns JSON as a dictionary from a given URL.

    :param str url:
    :param bool allow_empty:
    :rtype: dict
    """
    try:
        response = requests.get(url)
        json = response.json()

    except ValueError:
        if not allow_empty:
            raise
        json = {}

    return json


def get_user_agent(faked=False):
    """Returns User Agent string.

    :param bool faked: Whether to use faked agent to satisfy proxy or similar.
    :rtype: str
    """
    if faked:
        agent = 'curl/7.21.4 (universal-apple-darwin11.0) libcurl/7.21.4 OpenSSL/0.9.8r zlib/1.2.5'

    else:
        from bowerer import VERSION
        from platform import platform
        agent = 'bowerer/%s (%s)' % ('.'.join(map(str, VERSION)), platform(terse=True))

    return agent


class Endpoint(object):
    """Stuff to work with endpoint notations."""

    RE_ENDPOINT = re.compile('^(?:([\w\-]|(?:[\w\.\-]+[\w\-])?)=)?([^\|#]+)(?:#(.*))?$', re.U)
    RE_SOURCE = re.compile(r'[\/\\@]', re.U)

    @classmethod
    def is_wildcard(cls, val):
        return not val or val == '*' or val == 'latest'

    @classmethod
    def compose(cls, decomposed_dict):
        """Composes endpoint string from dict.

        :param dict decomposed_dict:
        :rtype: str
        """
        composed = ''

        def get(key):
            return decomposed_dict.get(key, '').strip()

        name = get('name')

        if name:
            composed = '%s%s=' % (composed, name)

        source = get('source')
        composed = '%s%s' % (composed, source)

        target = get('target')
        if not cls.is_wildcard(target):
            composed = '%s#%s' % (composed, target)

        return composed

    @classmethod
    def decompose(cls, endpoint):
        """Decomposed endpoint string into dict.

        :param str endpoint:
        :rtype: dict
        """
        match = cls.RE_ENDPOINT.match(endpoint)

        if not match:
            raise EndpointError('Invalid endpoint: %s' % endpoint)

        target = (match.group(3) or '').strip()

        return {
            'name': (match.group(1) or '').strip(),
            'source': (match.group(2) or '').strip(),
            'target': '*' if cls.is_wildcard(target) else target
        }

    @classmethod
    def decompose_from_json(cls, key, val):
        """Decomposes endpoint described as JSON key-value pair into dict

        :param str key:
        :param str val:
        :rtype: dict
        """
        key = (key or '').strip()
        val = (val or '').strip()

        if not key:
            raise EndpointError('The key must be specified')

        endpoint = '%s=' % key
        split = [item.strip() for item in val.split('#')]

        if len(split) > 1:
            # If # was found, the source was specified
            endpoint += (split[0] or key) + '#' + split[1]

        elif cls.RE_SOURCE.findall(val):
            # Check if value looks like a source
            endpoint += val + '#*'

        else:
            # Otherwise use the key as the source
            endpoint += key + '#' + split[0]

        return cls.decompose(endpoint)

    @classmethod
    def compose_to_json(cls, decomposed_dict):
        """Composes a JSON-ready dict from decomposed endpoint dict.

        :param dict decomposed_dict:
        :rtype: dict
        """

        def get(key):
            return decomposed_dict.get(key, '').strip()

        name = get('name')
        if not name:
            raise EndpointError('Decomposed endpoint must have a name')

        value = ''

        source = get('source')
        if source != name:
            value += source

        target = get('target')
        if not value:
            if cls.is_wildcard(target):
                value += '*'
            else:
                if '/' in target:
                    value += '#' + target
                else:
                    value += target

        elif not cls.is_wildcard(target) or not cls.RE_SOURCE.findall(source):
            value += '#' + (target or '*')

        return {name: value}


class JsonReader(object):

    filename_component = 'component.json'
    filename_deprecated = filename_component
    filename_modern = 'bower.json'
    filename_modern_hidden = '.' + filename_modern
    candidate_filenames = (filename_modern, filename_deprecated, filename_modern_hidden)

    def __init__(self, path):
        self.path = path

    def read(self):
        filepath = self.path

        LOGGER.debug('Trying to read project JSON from %s ...', filepath)

        if isdir(filepath):
            filepath = self.find(filepath)

        if not self.exists(filepath):
            raise JsonError('File does not exist %s' % filepath)

        contents = self.read_(filepath)

        return filepath, contents

    @classmethod
    def find(cls, path, candidates=None):
        LOGGER.debug('Scanning %s ...', path)

        if candidates is None:
            candidates = cls.candidate_filenames

        if not candidates:
            raise JsonError('None of %s were found in %s' % (', '.join(cls.candidate_filenames), path))

        current_candidate = candidates[0]
        LOGGER.debug('Current candidate: %s', current_candidate)

        filepath = cls.resolve(path, current_candidate)
        if not cls.exists(filepath):
            filepath = cls.find(path, candidates[1:])

            if current_candidate != cls.filename_component:
                return filepath

            if not cls.is_component_one(cls.read_(filepath)):
                return filepath

            return cls.find(path, candidates[2:])

        return filepath

    @classmethod
    def read_(cls, filepath):
        with open(filepath) as f:
            contents = json.load(f)
        return contents

    @classmethod
    def resolve(cls, path, filename):
        return abspath(join(path, filename))

    @classmethod
    def exists(cls, filepath):
        return exists(filepath)

    @classmethod
    def validate(cls, json_dict):
        """Validates a given JSON dict.

        :param dict json_dict:
        :raises: JsonError
        """
        if not json_dict.get('name'):
            raise JsonError('`name` property is not set')

    @classmethod
    def normalize(cls, json_dict):
        """Normalizes a given JSON dict inplace.

        :param dict json_dict:
        """
        main = json_dict.get('main')
        if isinstance(main, string_types):
            json_dict['main'] = main.split(',')

    @classmethod
    def is_component_one(cls, json_dict):
        """Verifies JSON is component(1) spec conformed.

        :param dict json_dict:
        :rtype: bool
        """
        component_one_keys = ('repo', 'development', 'local', 'remotes', 'paths', 'demo')
        return set(json_dict.keys()).intersection(component_one_keys)


def read_json(path, dummy_json=None):
    deprecated = False
    is_dummy = False

    try:
        filepath, contents = JsonReader(path).read()
        filename = basename(filepath)
        if filename == JsonReader.filename_deprecated:
            deprecated = filename

    except JsonError:
        if not dummy_json:
            raise
        contents = dummy_json
        is_dummy = True

    return contents, deprecated, is_dummy
