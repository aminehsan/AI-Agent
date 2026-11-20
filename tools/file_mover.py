from dataclasses import dataclass
from pathlib import Path

from .utility import format_path, resolve_linked_project_path, resolve_new_project_path
from .validate import validate_file_path


@dataclass(frozen=True, slots=True)
class _FileMoveResult:
    source_path: Path
    destination_path: Path
    source_is_linked: bool
    destination_is_linked: bool


class FileMover:
    @staticmethod
    def _move(source_path: Path, destination_path: Path) -> _FileMoveResult:
        resolved_source, source_is_linked = resolve_linked_project_path(source_path)
        if source_path.is_symlink():
            raise ValueError(f"Source path must not be a symbolic link: {source_path}")
        validate_file_path(resolved_source)

        resolved_destination, destination_is_linked = resolve_new_project_path(destination_path)
        if resolved_destination.exists(follow_symlinks=False):
            raise FileExistsError(f"Destination path already exists: {destination_path}")

        resolved_source.rename(resolved_destination)

        return _FileMoveResult(
            source_path, destination_path, source_is_linked, destination_is_linked
        )

    @staticmethod
    def _format_result(result: _FileMoveResult) -> str:
        return (
            f"Source {format_path(result.source_path, result.source_is_linked)}\n"
            f"Destination {format_path(result.destination_path, result.destination_is_linked)}\n"
            "Status: moved"
        )

    @classmethod
    def move_file(cls, source_path: str, destination_path: str) -> str:
        """
        Move or rename an existing regular file to an unused path on the same filesystem. To rename it, provide the full destination path with the new filename, either in the same directory or in a different directory.
        Both supplied paths and their resolved paths must be inside the project and outside excluded directories.
        Args:
            source_path: Absolute path of the file to move. Symbolic links are not accepted as files.
            destination_path: Absolute path including the desired file name. Its parent must exist.
        Returns:
            The requested source and destination paths and move status.
        """

        return cls._format_result(cls._move(Path(source_path), Path(destination_path)))
