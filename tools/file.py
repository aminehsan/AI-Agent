from pathlib import Path


class FileReader:
    @staticmethod
    def _read_text(
        path: Path,
        *,
        start_line: int,
        end_line: int | None,
    ) -> tuple[Path, tuple, int]:
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

        lines: list[str] = []
        try:
            with resolved_path.open("r", encoding="utf-8") as file:
                for line_number, line in enumerate(file, start=1):
                    if line_number < start_line:
                        continue
                    if end_line is not None and line_number > end_line:
                        break
                    if "\x00" in line:
                        raise ValueError(f"File appears to contain binary data: {resolved_path}")
                    lines.append(line)
        except UnicodeDecodeError as error:
            raise ValueError(f"File is not valid UTF-8 text: {resolved_path}") from error

        return resolved_path, tuple(lines), start_line

    @staticmethod
    def _format_result(result: tuple[Path, tuple, int]) -> str:
        path, lines, first_line = result
        if not lines:
            return f"Path: {path}\nNo content found from line {first_line}."

        last_line = first_line + len(lines) - 1
        line_number_width = len(str(last_line))
        content = "".join(
            f"{line_number:>{line_number_width}} | {line}"
            for line_number, line in enumerate(lines, start=first_line)
        )

        return f"Path: {path}\nLines: {first_line}-{last_line}\n{content}"

    def read_file(
        self,
        path: Path,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> str:
        """
        Read UTF-8 text from an absolute file path.

        Args:
            path: Absolute filesystem path of the text file to inspect.
            start_line: First line to return, using one-based numbering.
            end_line: Last line to return, inclusive; null reads to end of file.

        Returns:
            The resolved path, selected line range, and line-numbered text.
        """
        return self._format_result(
            self._read_text(
                path,
                start_line=start_line,
                end_line=end_line,
            )
        )
