from dataclasses import dataclass
from pathlib import Path

from .utility import is_linked_project_path, resolve_project_path
from .validate import (
    validate_directory_parent_path,
    validate_logical_project_path,
    validate_non_excluded_project_path,
)


@dataclass(frozen=True, slots=True)
class FileCreationResult:
    path: Path
    character_count: int
    is_linked: bool


class FileCreator:
    @staticmethod
    def _create(path: Path, content: str, encoding: str) -> FileCreationResult:
        validate_logical_project_path(path)
        is_linked = is_linked_project_path(path.parent)
        resolved_parent = resolve_project_path(path.parent)
        validate_directory_parent_path(resolved_parent)

        resolved_path = resolved_parent / path.name
        validate_non_excluded_project_path(resolved_path)
        file_created = False
        try:
            with resolved_path.open("x", encoding=encoding, newline="") as file:
                file_created = True
                character_count = file.write(content)
        except Exception:
            if file_created:
                resolved_path.unlink(missing_ok=True)
            raise

        return FileCreationResult(path, character_count, is_linked)

    @staticmethod
    def _format_result(result: FileCreationResult) -> str:
        link_status = "\nLink: yes" if result.is_linked else ""
        return f"Path: {result.path}{link_status}\nStatus: created\nCharacters: {result.character_count}"

    def create_file(self, path: str, content: str, encoding: str = "utf-8") -> str:
        """
        Create a new text file at an absolute path.

        Args:
            path: Absolute path of a new text file inside the project and outside excluded directories.
            content: Text to write exactly as provided.
            encoding: Text encoding used to write the file; defaults to utf-8.

        Returns:
            The requested path, creation status, and number of characters written.
        """

        return self._format_result(self._create(Path(path), content, encoding))
