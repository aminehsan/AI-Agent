from dataclasses import dataclass
from pathlib import Path

from .utility import format_path, resolve_new_project_path


@dataclass(frozen=True, slots=True)
class _DirectoryCreationResult:
    path: Path
    is_linked: bool


class DirectoryCreator:
    @staticmethod
    def _create(path: Path) -> _DirectoryCreationResult:
        resolved_path, is_linked = resolve_new_project_path(path)
        resolved_path.mkdir()
        return _DirectoryCreationResult(path, is_linked)

    @staticmethod
    def _format_result(result: _DirectoryCreationResult) -> str:
        return f"{format_path(result.path, result.is_linked)}\nStatus: created"

    def create_directory(self, path: str) -> str:
        """
        Create a new directory at an absolute path.

        Args:
            path: Absolute path of a new directory inside the project and outside excluded directories.

        Returns:
            The requested path and creation status.
        """

        return self._format_result(self._create(Path(path)))
