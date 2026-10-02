from pathlib import Path

from settings import settings


def validate_path(path: Path) -> Path:
    project_root = settings.project_root
    if not path.is_relative_to(project_root):
        raise ValueError(f"Path must be inside project root: {project_root}. Received: {path}")
    return path
