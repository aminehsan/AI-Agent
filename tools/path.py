from config import settings


def project_path() -> str:
    """The absolute path of the project you are working on."""

    return str(settings.project_root)
