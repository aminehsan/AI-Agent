from dataclasses import dataclass
from pathlib import Path

DEFAULT_ENCODING = "utf-8"
DEFAULT_MAX_CHARACTERS = 100_000


@dataclass(frozen=True, slots=True)
class ReadFileResult:
    path: Path
    lines: tuple[str, ...]
    first_line: int
    truncated: bool
    next_line: int | None
    partial_last_line: bool


def read_text_file(
    path: str | Path,
    *,
    start_line: int = 1,
    end_line: int | None = None,
    encoding: str = DEFAULT_ENCODING,
    max_characters: int = DEFAULT_MAX_CHARACTERS,
) -> ReadFileResult:
    """Read a bounded range from a text file at any filesystem location."""
    if not str(path).strip():
        raise ValueError("File path cannot be empty.")
    if start_line < 1:
        raise ValueError("start_line must be greater than or equal to 1.")
    if end_line is not None and end_line < start_line:
        raise ValueError("end_line must be greater than or equal to start_line.")
    if not encoding.strip():
        raise ValueError("encoding cannot be empty.")
    if max_characters < 1:
        raise ValueError("max_characters must be greater than or equal to 1.")

    try:
        resolved_path = Path(path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValueError(f"Cannot resolve file path: {path}") from error

    if not resolved_path.is_file():
        raise ValueError(f"Path is not a regular file: {resolved_path}")

    lines: list[str] = []
    character_count = 0
    truncated = False
    next_line: int | None = None
    partial_last_line = False

    try:
        with resolved_path.open("r", encoding=encoding, errors="strict", newline="") as file:
            for line_number, line in enumerate(file, start=1):
                if line_number < start_line:
                    continue
                if end_line is not None and line_number > end_line:
                    break
                if "\x00" in line:
                    raise ValueError(f"File appears to contain binary data: {resolved_path}")

                remaining_characters = max_characters - character_count
                if len(line) > remaining_characters:
                    if remaining_characters:
                        lines.append(line[:remaining_characters])
                        partial_last_line = True
                    truncated = True
                    next_line = line_number
                    break

                lines.append(line)
                character_count += len(line)
    except LookupError as error:
        raise ValueError(f"Unknown text encoding: {encoding}") from error
    except UnicodeDecodeError as error:
        raise ValueError(
            f"File is not valid {encoding} text: {resolved_path}"
        ) from error
    except OSError as error:
        raise OSError(f"Cannot read file: {resolved_path}") from error

    return ReadFileResult(
        path=resolved_path,
        lines=tuple(lines),
        first_line=start_line,
        truncated=truncated,
        next_line=next_line,
        partial_last_line=partial_last_line,
    )


def _format_result(result: ReadFileResult) -> str:
    if not result.lines:
        return f"Path: {result.path}\nNo content found from line {result.first_line}."

    last_line = result.first_line + len(result.lines) - 1
    line_number_width = len(str(last_line))
    content = "".join(
        f"{line_number:>{line_number_width}} | {line}"
        for line_number, line in enumerate(result.lines, start=result.first_line)
    )
    if content and not content.endswith(("\n", "\r")):
        content += "\n"

    output = f"Path: {result.path}\nLines: {result.first_line}-{last_line}\n{content}"
    if result.truncated:
        detail = " within" if result.partial_last_line else " before"
        output += (
            f"[Output truncated{detail} line {result.next_line} at "
            f"{DEFAULT_MAX_CHARACTERS:,} characters.]"
        )
    return output.rstrip()


def read_file(
    path: str,
    start_line: int = 1,
    end_line: int | None = None,
    encoding: str = DEFAULT_ENCODING,
) -> str:
    """Read a text file, including files outside the current project.

    Args:
        path: Absolute path, or a path relative to the process working directory.
        start_line: First line to read, using one-based line numbers.
        end_line: Last line to read (inclusive), or null to continue to the output limit.
        encoding: Text encoding used to decode the file.
    """
    return _format_result(
        read_text_file(
            path,
            start_line=start_line,
            end_line=end_line,
            encoding=encoding,
        )
    )
