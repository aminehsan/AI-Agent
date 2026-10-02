from dataclasses import dataclass
from pathlib import Path

from tools.validate import validate_path


@dataclass(frozen=True, slots=True)
class Result:
    path: Path
    lines: tuple[str, ...]
    first_line: int


class FileRead:
    @staticmethod
    def _read(path: Path, start_line: int, end_line: int | None, encoding: str) -> Result:
        if not path.is_absolute():
            raise ValueError("File path must be absolute.")
        if start_line < 1:
            raise ValueError("start_line must be greater than or equal to 1.")
        if end_line is not None and end_line < start_line:
            raise ValueError("end_line must be greater than or equal to start_line.")
        try:
            resolved_path = path.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise ValueError(f"Cannot resolve file path: {path}") from error
        validate_path(resolved_path)
        if not resolved_path.is_file():
            raise ValueError(f"Path is not a regular file: {resolved_path}")

        selected_lines: list[str] = []
        with resolved_path.open("r", encoding=encoding, errors="strict", newline="") as file:
            for line_number, line in enumerate(file, start=1):
                if line_number < start_line:
                    continue
                if end_line is not None and line_number > end_line:
                    break
                selected_lines.append(line)

        return Result(resolved_path, tuple(selected_lines), start_line)

    @staticmethod
    def _format(result: Result) -> dict[str, str]:
        path = str(result.path)
        if not result.lines:
            return {
                "path": path,
                "content": f"No content found from line {result.first_line}",
            }

        last_line = result.first_line + len(result.lines) - 1
        width = len(str(last_line))
        content = "".join(
            f"{number:>{width}}|{line}"
            for number, line in enumerate(result.lines, start=result.first_line)
        )

        return {
            "path": path,
            "lines": f"{result.first_line} - {last_line}",
            "content": content,
        }

    def read_file(
        self,
        path: str,
        start_line: int = 1,
        end_line: int | None = None,
        encoding: str = "utf-8",
    ) -> dict[str, str]:
        """
        Read text from an absolute file path.

        Args:
            path: Absolute path of a text file inside the project.
            start_line: First line to return, using one-based numbering; defaults to 1.
            end_line: Last line to return, inclusive; null reads to end of file; defaults to None.
            encoding: Text encoding used to read the file; defaults to utf-8.

        Returns:
            The resolved path, selected line range, and line-numbered text.
        """

        return self._format(self._read(Path(path), start_line, end_line, encoding))
