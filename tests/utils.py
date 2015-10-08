import unittest
from functools import partial

from bowerer.utils import Endpoint
from bowerer.exceptions import EndpointError


class EndpointsTest(unittest.TestCase):

    def check(self, method, variants, expected):

        if not isinstance(variants, list):
            variants = [variants]

        [self.assertEqual(method(rule), expected) for rule in variants]

    def test_compose(self):

        check = partial(self.check, Endpoint.compose)

        check({'name': '', 'source': 'jquery', 'target': '~2.0.0'}, 'jquery#~2.0.0')

        check([
            {'name': '', 'source': 'jquery', 'target': '*'},
            {'name': '', 'source': 'jquery', 'target': 'latest'},
            {'name': '', 'source': 'jquery', 'target': ''}
        ], 'jquery')

        check(
            {'name': '', 'source': 'jquery', 'target': '3dc50c62fe2d2d01afc58e7ad42236a35acff4d8'},
            'jquery#3dc50c62fe2d2d01afc58e7ad42236a35acff4d8')

        check({'name': '', 'source': 'jquery', 'target': 'master'}, 'jquery#master')

        check({'name': 'backbone', 'source': 'backbone-amd', 'target': '~1.0.0'}, 'backbone=backbone-amd#~1.0.0')
        check({'name': 'backbone', 'source': 'backbone-amd', 'target': '*'}, 'backbone=backbone-amd')
        check({'name': 'backbone', 'source': 'backbone-amd', 'target': ''}, 'backbone=backbone-amd')

        check(
            {'name': '', 'source': 'http://twitter.github.io/bootstrap/assets/bootstrap.zip', 'target': '*'},
            'http://twitter.github.io/bootstrap/assets/bootstrap.zip')

        check(
            {'name': 'bootstrap', 'source': 'http://twitter.github.io/bootstrap/assets/bootstrap.zip', 'target': '*'},
            'bootstrap=http://twitter.github.io/bootstrap/assets/bootstrap.zip')

        check({'name': ' foo ', 'source': ' bar ', 'target': ' ~1.0.2 '}, 'foo=bar#~1.0.2')
        check({'name': ' foo ', 'source': ' foo ', 'target': ' ~1.0.2 '}, 'foo=foo#~1.0.2')
        check({'name': ' foo ', 'source': ' foo ', 'target': ' * '}, 'foo=foo')
        check({'name': ' ', 'source': ' foo ', 'target': ''}, 'foo')

    def test_decompose(self):

        check = partial(self.check, Endpoint.decompose)

        check('jquery#~2.0.0', {'name': '', 'source': 'jquery', 'target': '~2.0.0'})
        check('jquery#*', {'name': '', 'source': 'jquery', 'target': '*'})
        check('jquery#latest', {'name': '', 'source': 'jquery', 'target': '*'})
        check(
            'jquery#3dc50c62fe2d2d01afc58e7ad42236a35acff4d8',
            {'name': '', 'source': 'jquery', 'target': '3dc50c62fe2d2d01afc58e7ad42236a35acff4d8'})
        check('jquery#master', {'name': '', 'source': 'jquery', 'target': 'master'})
        check('backbone=backbone-amd#~1.0.0', {'name': 'backbone', 'source': 'backbone-amd', 'target': '~1.0.0'})
        check('backbone=backbone-amd#latest', {'name': 'backbone', 'source': 'backbone-amd', 'target': '*'})
        check('backbone=backbone-amd#*', {'name': 'backbone', 'source': 'backbone-amd', 'target': '*'})
        check(
            'http://twitter.github.io/bootstrap/assets/bootstrap.zip',
            {'name': '', 'source': 'http://twitter.github.io/bootstrap/assets/bootstrap.zip', 'target': '*'})
        check(
            'bootstrap=http://twitter.github.io/bootstrap/assets/bootstrap.zip',
            {'name': 'bootstrap', 'source': 'http://twitter.github.io/bootstrap/assets/bootstrap.zip', 'target': '*'})
        check(
            'bootstrap=http://twitter.github.io/bootstrap/assets/bootstrap.zip#latest',
            {'name': 'bootstrap', 'source': 'http://twitter.github.io/bootstrap/assets/bootstrap.zip', 'target': '*'})

        decomposed = Endpoint.decompose('foo= source # ~1.0.2 ')
        self.assertEqual(decomposed['source'], 'source')
        self.assertEqual(decomposed['target'], '~1.0.2')

        decomposed = Endpoint.decompose('foo= source # latest')
        self.assertEqual(decomposed['source'], 'source')
        self.assertEqual(decomposed['target'], '*')

        decomposed = Endpoint.decompose('foo= source # *')
        self.assertEqual(decomposed['source'], 'source')
        self.assertEqual(decomposed['target'], '*')

    def test_decompose_from_json(self):

        mapping = [
            (('jquery', '~1.9.1'),
             (' jquery ', ' ~1.9.1 '),
             {'name': 'jquery', 'source': 'jquery', 'target': '~1.9.1'}),
            (('foo', 'latest'),
             (' foo ', ' latest '),
             {'name': 'foo', 'source': 'foo', 'target': '*'}),
            (('bar', '*'),
             (' bar ', ' * '),
             {'name': 'bar', 'source': 'bar', 'target': '*'}),
            (('baz', '#~0.2.0'),
             (' baz ', '# ~0.2.0 '),
             {'name': 'baz', 'source': 'baz', 'target': '~0.2.0'}),
            (('backbone', 'backbone-amd#~1.0.0'),
             (' backbone ', ' backbone-amd#~1.0.0 '),
             {'name': 'backbone', 'source': 'backbone-amd', 'target': '~1.0.0'}),
            (('backbone2', 'backbone=backbone-amd#~1.0.0'),
             (' backbone2 ', ' backbone=backbone-amd # ~1.0.0 '),
             {'name': 'backbone2', 'source': 'backbone=backbone-amd', 'target': '~1.0.0'}),
            (('bootstrap', 'http://twitter.github.io/bootstrap/assets/bootstrap'),
             (' bootstrap ', ' http://twitter.github.io/bootstrap/assets/bootstrap'),
             {'name': 'bootstrap', 'source': 'http://twitter.github.io/bootstrap/assets/bootstrap', 'target': '*'}),
            (('bootstrap2', 'http://twitter.github.io/bootstrap/assets/bootstrap#*'),
             (' bootstrap2 ', ' http://twitter.github.io/bootstrap/assets/bootstrap # *'),
             {'name': 'bootstrap2', 'source': 'http://twitter.github.io/bootstrap/assets/bootstrap', 'target': '*'}),
            (('ssh', 'git@example.com'),
             (' ssh ', ' git@example.com '),
             {'name': 'ssh', 'source': 'git@example.com', 'target': '*'}),
            (('git', 'git://example.com'),
             (' git ', ' git://example.com '),
             {'name': 'git', 'source': 'git://example.com', 'target': '*'}),
            (('path', '/foo'),
             (' path ', ' /foo '),
             {'name': 'path', 'source': '/foo', 'target': '*'}),
            (('winpath', 'c:\\foo'),
             (' winpath ', ' c:\\foo '),
             {'name': 'winpath', 'source': 'c:\\foo', 'target': '*'}),
        ]

        for (k, v), (k1, v1), expected in mapping:
            self.assertEqual(Endpoint.decompose_from_json(k, v), expected)
            self.assertEqual(Endpoint.decompose_from_json(k1, v1), expected)  # strip() check

        self.assertRaises(EndpointError, Endpoint.decompose_from_json, None, None)
        self.assertRaises(EndpointError, Endpoint.decompose_from_json, '', '')

    def test_decomposed_to_json(self):
        mapping = [
            ({'name': 'jquery', 'source': 'jquery', 'target': '~1.9.1'},
             {'name': ' jquery ', 'source': ' jquery ', 'target': ' ~1.9.1 '},
             {'jquery': '~1.9.1'}),
            ({'name': 'foo', 'source': 'foo', 'target': 'latest'},
             {'name': 'foo', 'source': ' foo', 'target': ' latest '},
             {'foo': '*'}),
            ({'name': 'bar', 'source': 'bar', 'target': '*'},
             {'name': 'bar', 'source': 'bar ', 'target': ' * '},
             {'bar': '*'}),
            ({'name': 'baz', 'source': 'baz', 'target': ''},
             {'name': 'baz ', 'source': 'baz', 'target': ' '},
             {'baz': '*'}),
            ({'name': 'jqueryx', 'source': 'jquery', 'target': '~1.9.1'},
             {'name': ' jqueryx ', 'source': ' jquery ', 'target': ' ~1.9.1 '},
             {'jqueryx': 'jquery#~1.9.1'}),
            ({'name': 'jqueryy', 'source': 'jquery-x', 'target': ''},
             {'name': ' jqueryy ', 'source': ' jquery-x ', 'target': ' '},
             {'jqueryy': 'jquery-x#*'}),
            ({'name': 'jqueryy', 'source': 'jquery-x', 'target': '*'},
             {'name': ' jqueryy ', 'source': ' jquery-x ', 'target': ' * '},
             {'jqueryy': 'jquery-x#*'}),
            ({'name': 'backbone', 'source': 'backbone-amd', 'target': '~1.0.0'},
             {'name': ' backbone ', 'source': ' backbone-amd ', 'target': ' ~1.0.0 '},
             {'backbone': 'backbone-amd#~1.0.0'}),
            ({'name': 'backbone', 'source': 'backbone=backbone-amd', 'target': '~1.0.0'},
             {'name': ' backbone ', 'source': ' backbone=backbone-amd ', 'target': ' ~1.0.0 '},
             {'backbone': 'backbone=backbone-amd#~1.0.0'}),
            ({'name': 'bootstrap', 'source': 'http://twitter.github.io/bootstrap/assets/bootstrap', 'target': ''},
             {'name': ' bootstrap ', 'source': ' http://twitter.github.io/bootstrap/assets/bootstrap ', 'target': ' '},
             {'bootstrap': 'http://twitter.github.io/bootstrap/assets/bootstrap'}),
            ({'name': 'bootstrap', 'source': 'http://twitter.github.io/bootstrap/assets/bootstrap', 'target': '*'},
             {'name': ' bootstrap ', 'source': ' http://twitter.github.io/bootstrap/assets/bootstrap ', 'target': ' * '},
             {'bootstrap': 'http://twitter.github.io/bootstrap/assets/bootstrap'}),
            ({'name': 'ssh', 'source': 'git@example.com', 'target': '*'},
             {'name': ' ssh ', 'source': ' git@example.com ', 'target': ' * '},
             {'ssh': 'git@example.com'}),
            ({'name': 'git', 'source': 'git://example.com', 'target': '*'},
             {'name': ' git ', 'source': ' git://example.com ', 'target': ' * '},
             {'git': 'git://example.com'}),
            ({'name': 'ckeditor', 'source': 'ckeditor', 'target': 'full/4.3.3'},
             {'name': ' ckeditor ', 'source': ' ckeditor ', 'target': ' full/4.3.3 '},
             {'ckeditor': '#full/4.3.3'})
        ]

        for dec_dict, dec_dict_to_strip, expected in mapping:
            self.assertEqual(Endpoint.compose_to_json(dec_dict), expected)
            self.assertEqual(Endpoint.compose_to_json(dec_dict_to_strip), expected)  # strip() check

        self.assertRaises(EndpointError, Endpoint.compose_to_json, {'name': '', 'source': 'jquery', 'target': '*'})
        self.assertRaises(EndpointError, Endpoint.compose_to_json, {'name': ' ', 'source': 'jquery', 'target': '*'})
