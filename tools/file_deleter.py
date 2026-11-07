from dataclasses import dataclass
from pathlib import Path

from .utility import is_linked_project_path, resolve_project_path
from .validate import (
    validate_file_path,
    validate_logical_project_path,
)


@dataclass(frozen=True, slots=True)
class FileDeletionResult:
    path: Path
    is_link: bool
    is_linked: bool


class FileDeleter:
    @staticmethod
    def _delete(path: Path) -> FileDeletionResult:
        validate_logical_project_path(path)
        is_linked = is_linked_project_path(path.parent)
        resolve_project_path(path.parent)
        if path.is_symlink() and not path.is_dir():
            path.unlink()
            return FileDeletionResult(path, True, True)

        resolved_path = resolve_project_path(path)
        validate_file_path(resolved_path)

        resolved_path.unlink()
        return FileDeletionResult(path, False, is_linked)

    @staticmethod
    def _format_result(result: FileDeletionResult) -> str:
        status = "link deleted" if result.is_link else "deleted"
        link_status = "\nLink: yes" if result.is_linked else ""
        return f"Path: {result.path}{link_status}\nStatus: {status}"

    def delete_file(self, path: str) -> str:
        """
        Permanently delete a file or its symbolic link at an absolute path.

        Args:
            path: Absolute path of a file inside the project and outside excluded directories; deleting a file link removes only the link.

        Returns:
            The requested path and deletion status.
        """

        return self._format_result(self._delete(Path(path)))
