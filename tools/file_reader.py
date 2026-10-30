from dataclasses import dataclass
from pathlib import Path

from .validate import validate_absolute_path, validate_file_path, validate_project_path


@dataclass(frozen=True, slots=True)
class FileReadResult:
    path: Path
    content_lines: tuple[str, ...]
    first_line_number: int


class FileReader:
    @staticmethod
    def _read(
        path: Path,
        start_line: int,
        end_line: int | None,
        encoding: str,
    ) -> FileReadResult:
        validate_absolute_path(path)
        if start_line < 1:
            raise ValueError("start_line must be greater than or equal to 1.")
        if end_line is not None and end_line < start_line:
            raise ValueError("end_line must be greater than or equal to start_line.")
        resolved_path = path.resolve(strict=True)
        validate_project_path(resolved_path)
        validate_file_path(resolved_path)

        selected_lines: list[str] = []
        with resolved_path.open("r", encoding=encoding, errors="strict", newline="") as file:
            for line_number, line in enumerate(file, start=1):
                if line_number < start_line:
                    continue
                if end_line is not None and line_number > end_line:
                    break
                selected_lines.append(line)

        return FileReadResult(resolved_path, tuple(selected_lines), start_line)

    @staticmethod
    def _format_result(result: FileReadResult) -> str:
        path = str(result.path)
        if not result.content_lines:
            return f"Path: {path}\nContent: No content found from line {result.first_line_number}"

        last_line_number = result.first_line_number + len(result.content_lines) - 1
        line_number_width = len(str(last_line_number))
        content = "".join(
            f"{line_number:>{line_number_width}}|{line}"
            for line_number, line in enumerate(
                result.content_lines,
                start=result.first_line_number,
            )
        )

        return (
            f"Path: {path}\n"
            f"Lines: {result.first_line_number} - {last_line_number}\n"
            f"Content:\n{content}"
        )

    def read_file(
        self,
        path: str,
        start_line: int = 1,
        end_line: int | None = None,
        encoding: str = "utf-8",
    ) -> str:
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

        return self._format_result(self._read(Path(path), start_line, end_line, encoding))
