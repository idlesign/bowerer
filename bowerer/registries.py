from .utils import get_json


class Registry(object):

    def __init__(self, app_name):
        self.app_name = app_name


class Bower(Registry):

    TITLE = 'Bower Main'
    BASE_URL = 'http://bower.herokuapp.com'

    def get_app_data(self):
        return get_json('%s/packages/%s' % (self.BASE_URL, self.app_name))
