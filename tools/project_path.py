from settings import settings


def project_path() -> str:
    """The absolute path of the project you are working on."""

    return f"Path: {settings.project_root}"
