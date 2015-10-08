import re

import requests

from .exceptions import EndpointError


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
