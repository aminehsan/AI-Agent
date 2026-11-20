from dataclasses import dataclass
from pathlib import Path

from .utility import format_path, resolve_linked_project_path, resolve_new_project_path
from .validate import (
    validate_destination_outside_source_directory,
    validate_directory_path,
    validate_no_excluded_project_descendants,
    validate_non_linked_source_path,
    validate_non_project_root_path,
    validate_unused_destination_path,
)


@dataclass(frozen=True, slots=True)
class _DirectoryMoveResult:
    path: Path
    destination_path: Path
    source_is_linked: bool
    destination_is_linked: bool


class DirectoryMover:
    @staticmethod
    def _move(path: Path, destination_path: Path) -> _DirectoryMoveResult:
        resolved_source, source_is_linked = resolve_linked_project_path(path)
        validate_non_linked_source_path(path)
        validate_non_project_root_path(resolved_source)
        validate_directory_path(resolved_source)
        validate_no_excluded_project_descendants(resolved_source)

        resolved_destination, destination_is_linked = resolve_new_project_path(destination_path)
        validate_unused_destination_path(resolved_destination)
        validate_destination_outside_source_directory(resolved_source, destination_path)

        resolved_source.rename(resolved_destination)

        return _DirectoryMoveResult(path, destination_path, source_is_linked, destination_is_linked)

    @staticmethod
    def _format_result(result: _DirectoryMoveResult) -> str:
        return (
            f"Source {format_path(result.path, result.source_is_linked)}\n"
            f"Destination {format_path(result.destination_path, result.destination_is_linked)}\n"
            "Status: moved"
        )

    @classmethod
    def move_directory(cls, path: str, destination_path: str) -> str:
        """
        Move or rename an existing directory and all its contents to an unused path on the same filesystem.
        To rename it, provide the full destination path with the new directory name, either under the same parent directory or under a different one.
        Both supplied paths and their resolved paths must be inside the project and outside excluded directories.
        Args:
            path: Absolute path of the directory to move. The project root, symbolic links,
                junctions, and directories containing excluded project directories are ineligible.
            destination_path: Absolute path including the desired directory name. Its parent must exist outside the source directory.
        Returns:
            The requested source and destination paths and move status.
        """

        return cls._format_result(cls._move(Path(path), Path(destination_path)))
