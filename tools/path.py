from pathlib import Path
from settings import settings


def get_project_path() -> Path:
    """The path of the project you are working on."""
    return settings.project_root
