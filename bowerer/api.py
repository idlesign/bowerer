from .config import load
from .utils import Endpoint
from .project import Project


def install(endpoint, config, **options):
    # force_latest=False, production=False, save=False, save_dev=False, save_exact=False,
    config = load(config)
    endpoints = map(Endpoint.decompose, endpoint)
    project = Project(config)
    project.install(endpoints, options, config)
