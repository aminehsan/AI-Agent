from pathlib import Path

from settings import settings


def validate_project_path(path: Path) -> None:
    project_root = settings.project_root
    if not path.is_relative_to(project_root):
        raise ValueError(f"Path must be inside project root: {project_root}, received: {path}")


def validate_non_project_root_path(path: Path) -> None:
    if path == settings.project_root:
        raise ValueError(f"Path must not be the project root: {path}")


def validate_absolute_path(path: Path) -> None:
    if not path.is_absolute():
        raise ValueError(f"Path must be absolute: {path}")


def validate_directory_parent_path(path: Path) -> None:
    if not path.is_dir():
        raise ValueError(f"Parent path must be directory: {path}")


def validate_directory_path(path: Path) -> None:
    if not path.is_dir():
        raise ValueError(f"Path must be directory: {path}")


def validate_file_path(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"Path must be file: {path}")


def validate_non_link_path(path: Path) -> None:
    if path.is_symlink() or path.is_junction():
        raise ValueError(f"Path must not be a link: {path}")


def validate_non_excluded_project_directories_path(path: Path) -> None:
    directories = tuple(directory.resolve() for directory in settings.excluded_project_directories)
    if any(path.is_relative_to(directory) for directory in directories):
        raise ValueError(f"Path must not be inside an excluded project directory: {path}")
