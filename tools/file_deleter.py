from dataclasses import dataclass
from pathlib import Path

from .utility import format_path, resolve_linked_project_path, resolve_project_path
from .validate import (
    validate_file_path,
    validate_logical_project_path,
)


@dataclass(frozen=True, slots=True)
class _FileDeletionResult:
    path: Path
    is_link: bool
    is_linked: bool


class FileDeleter:
    @staticmethod
    def _delete(path: Path) -> _FileDeletionResult:
        validate_logical_project_path(path)

        _, is_linked = resolve_linked_project_path(path.parent)

        if path.is_symlink() and not path.is_dir():
            path.unlink()
            return _FileDeletionResult(path, True, True)

        resolved_path = resolve_project_path(path)
        validate_file_path(resolved_path)
        resolved_path.unlink()
        return _FileDeletionResult(path, False, is_linked)

    @staticmethod
    def _format_result(result: _FileDeletionResult) -> str:
        status = "link deleted" if result.is_link else "deleted"
        return f"{format_path(result.path, result.is_linked)}\nStatus: {status}"

    @classmethod
    def delete_file(cls, path: str) -> str:
        """
        Permanently delete a file or its symbolic link at an absolute path.

        Args:
            path: Absolute path of a file inside the project and outside excluded directories; deleting a file link removes only the link.

        Returns:
            The requested path and deletion status.
        """

        return cls._format_result(cls._delete(Path(path)))
