from os import name as os_name
from os import stat_result
from os.path import samestat
from pathlib import Path

from settings import settings

from .validate import (
    validate_directory_parent_path,
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


def should_skip_entry(entry: Path, excluded_names: frozenset[str], include_hidden: bool) -> bool:
    return (
        entry in settings.excluded_project_directories
        or entry.name in excluded_names
        or (not include_hidden and is_hidden_path(entry))
    )


def format_path(path: Path, is_linked: bool = False) -> str:
    return f"Path: {path}" + ("\nLink: yes" if is_linked else "")


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


def resolve_linked_project_path(
    path: Path, *, allow_external_link: bool = False
) -> tuple[Path, bool]:
    is_linked = is_linked_project_path(path)
    resolved_path = resolve_project_path(
        path, allow_external_link=allow_external_link and is_linked
    )
    return resolved_path, is_linked


def resolve_new_project_path(path: Path) -> tuple[Path, bool]:
    validate_logical_project_path(path)
    resolved_parent, is_linked = resolve_linked_project_path(path.parent)
    validate_directory_parent_path(resolved_parent)
    resolved_path = resolved_parent / path.name
    validate_non_excluded_project_path(resolved_path)
    return resolved_path, is_linked


def has_file_changed(path: Path, original_stat: stat_result) -> bool:
    current_stat = path.lstat()
    return (
        not samestat(original_stat, current_stat)
        or original_stat.st_mtime_ns != current_stat.st_mtime_ns
        or original_stat.st_size != current_stat.st_size
    )
