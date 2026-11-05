from os import name as os_name
from os import stat_result
from os.path import samestat
from pathlib import Path


def is_windows_os() -> bool:
    return os_name == "nt"


def is_hidden_path(path: Path) -> bool:
    if path.name.startswith("."):
        return True
    if is_windows_os():
        from stat import FILE_ATTRIBUTE_HIDDEN

        return bool(path.stat(follow_symlinks=False).st_file_attributes & FILE_ATTRIBUTE_HIDDEN)
    return False


def has_file_changed(path: Path, original_stat: stat_result) -> bool:
    current_stat = path.lstat()
    return (
        not samestat(original_stat, current_stat)
        or original_stat.st_mtime_ns != current_stat.st_mtime_ns
        or original_stat.st_size != current_stat.st_size
    )
