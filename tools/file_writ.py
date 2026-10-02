from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Result:
    path: Path
    characters_written: int


class FileWrit:
    @staticmethod
    def _write(path: Path, content: str, encoding: str) -> Result:
        if not path.is_absolute():
            raise ValueError("File path must be absolute.")

        parent = path.parent
        try:
            resolved_parent = parent.resolve(strict=True)
        except FileNotFoundError as error:
            raise ValueError(f"Parent directory does not exist: {parent}") from error
        except (OSError, RuntimeError) as error:
            raise ValueError(f"Cannot resolve parent directory: {parent}") from error

        if not resolved_parent.is_dir():
            raise ValueError(f"Parent path is not a directory: {resolved_parent}")

        resolved_path = resolved_parent / path.name
        try:
            with resolved_path.open("x", encoding=encoding, newline="") as file:
                characters_written = file.write(content)
        except FileExistsError as error:
            raise ValueError(f"File already exists: {resolved_path}") from error
        except OSError as error:
            raise ValueError(f"Cannot write file: {resolved_path}") from error

        return Result(
            path=resolved_path,
            characters_written=characters_written,
        )

    @staticmethod
    def _format(result: Result) -> str:
        return (
            f"Path: {result.path}\nStatus: created\nCharacters written: {result.characters_written}"
        )

    def run(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
    ) -> str:
        """
        Create a new UTF-8 text file.

        Args:
            path: Absolute filesystem path of the new text file.
            content: Text to write exactly as provided.
            encoding: Text encoding used to write the file; defaults to utf-8.

        Returns:
            The resolved path, creation status, and number of characters written.
        """

        return self._format(self._write(Path(path), content, encoding))
