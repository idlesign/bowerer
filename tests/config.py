import unittest
from functools import partial

from bowerer.config import parse_from_command_line


class ConfigTest(unittest.TestCase):

    def test_parse_from_command_line(self):
        args = [
            '--config.var=some_value',
            '--config.sub.first=value1',
            '--config.sub.second=value2',
        ]
        self.assertEqual(parse_from_command_line(args), {
            'var': 'some_value',
            'sub': {
                'first': 'value1',
                'second': 'value2',
            }
        })
