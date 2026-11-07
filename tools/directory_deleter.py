from dataclasses import dataclass
from pathlib import Path

from .utility import format_path, resolve_linked_project_path, resolve_project_path
from .validate import (
    validate_directory_path,
    validate_logical_project_path,
    validate_non_project_root_path,
)


@dataclass(frozen=True, slots=True)
class DirectoryDeletionResult:
    path: Path
    is_link: bool
    is_linked: bool


class DirectoryDeleter:
    @staticmethod
    def _delete(path: Path) -> DirectoryDeletionResult:
        validate_logical_project_path(path)
        validate_non_project_root_path(path)
        _, is_linked = resolve_linked_project_path(path.parent)
        if path.is_junction():
            path.rmdir()
            return DirectoryDeletionResult(path, True, True)
        if path.is_symlink() and path.is_dir():
            path.unlink()
            return DirectoryDeletionResult(path, True, True)

        resolved_path = resolve_project_path(path)
        validate_non_project_root_path(resolved_path)
        validate_directory_path(resolved_path)

        resolved_path.rmdir()
        return DirectoryDeletionResult(path, False, is_linked)

    @staticmethod
    def _format_result(result: DirectoryDeletionResult) -> str:
        status = "link deleted" if result.is_link else "deleted"
        return f"{format_path(result.path, result.is_linked)}\nStatus: {status}"

    def delete_directory(self, path: str) -> str:
        """
        Permanently delete an empty directory or its link at an absolute path.

        Args:
            path: Absolute path of an empty directory inside the project and outside excluded directories; deleting a directory link removes only the link.

        Returns:
            The requested path and deletion status.
        """

        return self._format_result(self._delete(Path(path)))
