import logging

LOGGER = logging.getLogger('Bowerer')

DEBUG = True

logging.basicConfig(format='%(message)s')
LOGGER.setLevel(logging.DEBUG if DEBUG else logging.INFO)
