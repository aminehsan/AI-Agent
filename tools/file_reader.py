from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class ReadResult:
    path: Path
    lines: tuple[str, ...]
    first_line: int


class FileReader:
    @staticmethod
    def _read_text(path: Path, *, start_line: int, end_line: int | None) -> ReadResult:
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
        if not resolved_path.is_file():
            raise ValueError(f"Path is not a regular file: {resolved_path}")

        try:
            text = resolved_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"File is not valid UTF-8 text: {resolved_path}") from error
        if "\x00" in text:
            raise ValueError(f"File appears to contain binary data: {resolved_path}")

        lines = text.splitlines(keepends=True)
        if text.endswith(("\n", "\r")):
            lines.append("")
        return ReadResult(
            path=resolved_path,
            lines=tuple(lines[start_line - 1 : end_line]),
            first_line=start_line,
        )

    @staticmethod
    def _format_result(result: ReadResult) -> str:
        if not result.lines:
            return f"Path: {result.path}\nNo content found from line {result.first_line}."

        last_line = result.first_line + len(result.lines) - 1
        width = len(str(last_line))
        content = "".join(
            f"{number:<{width}}|{line}"
            for number, line
            in enumerate(result.lines, start=result.first_line)
        )
        return (
            f"Path: {result.path}\n"
            f"Lines: {result.first_line}-{last_line}\n"
            f"Content:\n{content}"
        )

    def read(self, path: str, start_line: int = 1, end_line: int | None = None) -> str:
        return self._format_result(
            self._read_text(
                Path(path),
                start_line=start_line,
                end_line=end_line,
            )
        )
