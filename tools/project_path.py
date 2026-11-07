from settings import settings

from .utility import format_path


def get_project_path() -> str:
    """The absolute path of the project you are working on."""

    return format_path(settings.project_root)
