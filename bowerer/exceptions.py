class BowererException(Exception):
    pass


class UnsupportedHostingUrl(BowererException):
    pass


class EndpointError(BowererException):
    pass
