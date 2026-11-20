from dataclasses import dataclass
from pathlib import Path

from .utility import format_path, resolve_linked_project_path, resolve_new_project_path
from .validate import (
    validate_file_path,
    validate_non_linked_source_path,
    validate_unused_destination_path,
)


@dataclass(frozen=True, slots=True)
class _FileMoveResult:
    path: Path
    destination_path: Path
    source_is_linked: bool
    destination_is_linked: bool


class FileMover:
    @staticmethod
    def _move(path: Path, destination_path: Path) -> _FileMoveResult:
        resolved_source, source_is_linked = resolve_linked_project_path(path)
        validate_non_linked_source_path(path)
        validate_file_path(resolved_source)

        resolved_destination, destination_is_linked = resolve_new_project_path(destination_path)
        validate_unused_destination_path(resolved_destination)

        resolved_source.rename(resolved_destination)

        return _FileMoveResult(path, destination_path, source_is_linked, destination_is_linked)

    @staticmethod
    def _format_result(result: _FileMoveResult) -> str:
        return (
            f"Source {format_path(result.path, result.source_is_linked)}\n"
            f"Destination {format_path(result.destination_path, result.destination_is_linked)}\n"
            "Status: moved"
        )

    @classmethod
    def move_file(cls, path: str, destination_path: str) -> str:
        """
        Move or rename an existing regular file to an unused path on the same filesystem. To rename it, provide the full destination path with the new filename, either in the same directory or in a different directory.
        Both supplied paths and their resolved paths must be inside the project and outside excluded directories.
        Args:
            path: Absolute path of the file to move. Symbolic links are not accepted as files.
            destination_path: Absolute path including the desired file name. Its parent must exist.
        Returns:
            The requested source and destination paths and move status.
        """

        return cls._format_result(cls._move(Path(path), Path(destination_path)))
