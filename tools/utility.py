from os import name as os_name
from os import stat_result
from os.path import samestat
from pathlib import Path

from settings import settings

from .validate import (
    validate_logical_project_path,
    validate_non_excluded_project_path,
    validate_project_path,
)


def is_windows_os() -> bool:
    return os_name == "nt"


def is_hidden_path(path: Path) -> bool:
    if path.name.startswith("."):
        return True
    if is_windows_os():
        from stat import FILE_ATTRIBUTE_HIDDEN

        return bool(path.stat(follow_symlinks=False).st_file_attributes & FILE_ATTRIBUTE_HIDDEN)
    return False


def is_linked_project_path(path: Path) -> bool:
    validate_logical_project_path(path)
    current_path = settings.project_root
    is_linked = False
    for part in path.relative_to(current_path).parts:
        current_path /= part
        is_linked = is_linked or current_path.is_symlink() or current_path.is_junction()
    return is_linked


def resolve_project_path(path: Path, *, allow_external_link: bool = False) -> Path:
    validate_logical_project_path(path)
    resolved_path = path.resolve(strict=True)
    if resolved_path.is_relative_to(settings.project_root):
        validate_non_excluded_project_path(resolved_path)
    elif not allow_external_link:
        validate_project_path(resolved_path)
    return resolved_path


def has_file_changed(path: Path, original_stat: stat_result) -> bool:
    current_stat = path.lstat()
    return (
        not samestat(original_stat, current_stat)
        or original_stat.st_mtime_ns != current_stat.st_mtime_ns
        or original_stat.st_size != current_stat.st_size
    )
