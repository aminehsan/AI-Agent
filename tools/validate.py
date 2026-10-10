from pathlib import Path

from config import settings


def validate_absolute_path(path: Path) -> None:
    if not path.is_absolute():
        raise ValueError("Path must be absolute.")


def validate_project_path(path: Path) -> None:
    project_root = settings.project_root
    if not path.is_relative_to(project_root):
        raise ValueError(f"Path must be inside project root: {project_root}. Received: {path}")
