from dataclasses import dataclass
from pathlib import Path

from .utility import format_path, resolve_linked_project_path
from .validate import validate_file_path, validate_line_range


@dataclass(frozen=True, slots=True)
class _FileReadResult:
    path: Path
    content_lines: tuple[str, ...]
    first_line_number: int
    is_linked: bool


class FileReader:
    @staticmethod
    def _read(
        path: Path,
        start_line: int,
        end_line: int | None,
        encoding: str,
    ) -> _FileReadResult:
        validate_line_range(start_line, end_line)

        resolved_path, is_linked = resolve_linked_project_path(path, allow_external_link=True)

        validate_file_path(resolved_path)

        with resolved_path.open("r", encoding=encoding, errors="strict", newline="") as file:
            lines = file.read().splitlines(keepends=True)

        selected_lines = lines[start_line - 1 : end_line]
        return _FileReadResult(path, tuple(selected_lines), start_line, is_linked)

    @staticmethod
    def _format_result(result: _FileReadResult) -> str:
        header = format_path(result.path, result.is_linked)
        if not result.content_lines:
            return f"{header}\nContent: No content found from line {result.first_line_number}"

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
            f"{header}\nLines: {result.first_line_number} - {last_line_number}\nContent:\n{content}"
        )

    @classmethod
    def read_file(
        cls,
        path: str,
        start_line: int = 1,
        end_line: int | None = None,
        encoding: str = "utf-8",
    ) -> str:
        """
        Read text from an absolute file path.

        Args:
            path: Absolute path of a text file inside the project and outside excluded directories; links to external files may be read.
            start_line: First line to return, using one-based numbering; defaults to 1.
            end_line: Last line to return, inclusive; null reads to end of file; defaults to None.
            encoding: Text encoding used to read the file; defaults to utf-8.

        Returns:
            The requested path, selected line range, and line-numbered text.
        """

        return cls._format_result(cls._read(Path(path), start_line, end_line, encoding))
