from settings import settings


def get_project_path() -> str:
    """The path of the project you are working on."""

    return str(settings.project_root)
