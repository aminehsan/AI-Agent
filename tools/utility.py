from os import name as os_name
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
