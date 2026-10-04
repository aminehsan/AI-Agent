from dataclasses import dataclass
from pathlib import Path

from tools.validate import validate_absolute_path, validate_project_path


@dataclass(frozen=True, slots=True)
class Result:
    path: Path
    characters: int


class FileWrite:
    @staticmethod
    def _write(path: Path, content: str, encoding: str) -> Result:
        validate_absolute_path(path)
        parent = path.parent
        try:
            resolved_parent = parent.resolve(strict=True)
        except FileNotFoundError as error:
            raise ValueError(f"Parent directory does not exist: {parent}") from error
        except (OSError, RuntimeError) as error:
            raise ValueError(f"Cannot resolve parent directory: {parent}") from error
        validate_project_path(resolved_parent)
        if not resolved_parent.is_dir():
            raise ValueError(f"Parent path is not a directory: {resolved_parent}")

        resolved_path = resolved_parent / path.name
        try:
            with resolved_path.open("x", encoding=encoding, newline="") as file:
                characters = file.write(content)
        except FileExistsError as error:
            raise ValueError(f"File already exists: {resolved_path}") from error
        except OSError as error:
            raise ValueError(f"Cannot write file: {resolved_path}") from error

        return Result(resolved_path, characters)

    @staticmethod
    def _format(result: Result) -> dict[str, str | int]:
        return {
            "path": str(result.path),
            "status": "created",
            "characters": result.characters,
        }

    def write_file(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
    ) -> dict[str, str | int]:
        """
        Write a new text from an absolute file path.

        Args:
            path: Absolute path of a new text file inside the project.
            content: Text to write exactly as provided.
            encoding: Text encoding used to write the file; defaults to utf-8.

        Returns:
            The resolved path, creation status, and number of characters written.
        """

        return self._format(self._write(Path(path), content, encoding))
