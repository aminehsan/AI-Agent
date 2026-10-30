from dataclasses import dataclass
from pathlib import Path

from .validate import validate_absolute_path, validate_project_path


@dataclass(frozen=True, slots=True)
class DirectoryCreationResult:
    path: Path


class DirectoryCreator:
    @staticmethod
    def _create(path: Path) -> DirectoryCreationResult:
        validate_absolute_path(path)
        resolved_parent = path.parent.resolve(strict=True)
        validate_project_path(resolved_parent)
        if not resolved_parent.is_dir():
            raise ValueError(f"Parent path is not a directory: {resolved_parent}")

        resolved_path = resolved_parent / path.name
        resolved_path.mkdir()

        return DirectoryCreationResult(resolved_path)

    @staticmethod
    def _format_result(result: DirectoryCreationResult) -> str:
        return f"Path: {result.path}\nStatus: created"

    def create_directory(self, path: str) -> str:
        """
        Create a new directory at an absolute path.

        Args:
            path: Absolute path of a new directory inside the project.

        Returns:
            The resolved path and creation status.
        """

        return self._format_result(self._create(Path(path)))
