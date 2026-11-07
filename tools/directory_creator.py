from dataclasses import dataclass
from pathlib import Path

from .utility import is_linked_project_path, resolve_project_path
from .validate import (
    validate_directory_parent_path,
    validate_logical_project_path,
    validate_non_excluded_project_path,
)


@dataclass(frozen=True, slots=True)
class DirectoryCreationResult:
    path: Path
    is_linked: bool


class DirectoryCreator:
    @staticmethod
    def _create(path: Path) -> DirectoryCreationResult:
        validate_logical_project_path(path)
        is_linked = is_linked_project_path(path.parent)
        resolved_parent = resolve_project_path(path.parent)
        validate_directory_parent_path(resolved_parent)

        resolved_path = resolved_parent / path.name
        validate_non_excluded_project_path(resolved_path)
        resolved_path.mkdir()
        return DirectoryCreationResult(path, is_linked)

    @staticmethod
    def _format_result(result: DirectoryCreationResult) -> str:
        link_status = "\nLink: yes" if result.is_linked else ""
        return f"Path: {result.path}{link_status}\nStatus: created"

    def create_directory(self, path: str) -> str:
        """
        Create a new directory at an absolute path.

        Args:
            path: Absolute path of a new directory inside the project and outside excluded directories.

        Returns:
            The requested path and creation status.
        """

        return self._format_result(self._create(Path(path)))
