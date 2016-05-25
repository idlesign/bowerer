
class BowererException(Exception):
    pass


class UnsupportedHostingUrl(BowererException):
    pass


class EndpointError(BowererException):
    pass


class JsonError(BowererException):
    pass


class ProjectError(BowererException):
    pass
