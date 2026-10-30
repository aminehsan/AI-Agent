from dataclasses import dataclass
from pathlib import Path

from .validate import (
    validate_absolute_path,
    validate_directory_path,
    validate_non_excluded_project_path,
    validate_non_link_path,
    validate_non_project_root_path,
    validate_project_path,
)


@dataclass(frozen=True, slots=True)
class DirectoryDeletionResult:
    path: Path


class DirectoryDeleter:
    @staticmethod
    def _delete(path: Path) -> DirectoryDeletionResult:
        validate_absolute_path(path)
        validate_non_link_path(path)

        resolved_path = path.resolve(strict=True)
        validate_project_path(resolved_path)
        validate_non_project_root_path(resolved_path)
        validate_non_excluded_project_path(resolved_path)
        validate_directory_path(resolved_path)

        resolved_path.rmdir()
        return DirectoryDeletionResult(resolved_path)

    @staticmethod
    def _format_result(result: DirectoryDeletionResult) -> str:
        return f"Path: {result.path}\nStatus: deleted"

    def delete_directory(self, path: str) -> str:
        """
        Permanently delete an empty directory at an absolute path.

        Args:
            path: Absolute path of an empty directory inside the project and outside excluded directories; links are rejected.

        Returns:
            The resolved path and deletion status.
        """

        return self._format_result(self._delete(Path(path)))
