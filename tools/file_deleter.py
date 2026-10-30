from dataclasses import dataclass
from pathlib import Path

from .validate import (
    validate_absolute_path,
    validate_file_path,
    validate_non_link_path,
    validate_project_path,
)


@dataclass(frozen=True, slots=True)
class FileDeletionResult:
    path: Path


class FileDeleter:
    @staticmethod
    def _delete(path: Path) -> FileDeletionResult:
        validate_absolute_path(path)
        validate_non_link_path(path)

        resolved_path = path.resolve(strict=True)
        validate_project_path(resolved_path)
        validate_file_path(resolved_path)

        resolved_path.unlink()
        return FileDeletionResult(resolved_path)

    @staticmethod
    def _format_result(result: FileDeletionResult) -> str:
        return f"Path: {result.path}\nStatus: deleted"

    def delete_file(self, path: str) -> str:
        """
        Permanently delete a file at an absolute path.

        Args:
            path: Absolute path of a regular file inside the project; links are rejected.

        Returns:
            The resolved path and deletion status.
        """

        return self._format_result(self._delete(Path(path)))
