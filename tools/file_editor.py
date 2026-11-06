from dataclasses import dataclass
from os import fstat
from pathlib import Path

from .utility import has_file_changed
from .validate import (
    validate_absolute_path,
    validate_file_path,
    validate_non_excluded_project_path,
    validate_non_hard_link_path,
    validate_non_link_path,
    validate_project_path,
)


@dataclass(frozen=True, slots=True)
class FileEditResult:
    path: Path


class FileEditor:
    @staticmethod
    def _edit(path: Path, old_text: str, new_text: str, encoding: str) -> FileEditResult:
        validate_absolute_path(path)
        validate_non_link_path(path)
        if not old_text:
            raise ValueError("old_text must not be empty.")
        if old_text == new_text:
            raise ValueError("new_text must differ from old_text.")

        resolved_path = path.resolve(strict=True)
        validate_project_path(resolved_path)
        validate_non_excluded_project_path(resolved_path)
        validate_file_path(resolved_path)
        validate_non_hard_link_path(resolved_path)

        with resolved_path.open("r+", encoding=encoding, newline="") as file:
            original_stat = fstat(file.fileno())
            content = file.read()
            match_count = 0
            match_index = content.find(old_text)
            while match_index != -1:
                match_count += 1
                match_index = content.find(old_text, match_index + 1)
            if match_count != 1:
                raise ValueError(
                    f"old_text must occur exactly once; found {match_count} occurrences."
                )

            updated_content = content.replace(old_text, new_text, 1)

            if has_file_changed(resolved_path, original_stat):
                raise ValueError("The file changed during editing. Read it again before retrying.")

            try:
                file.seek(0)
                file.write(updated_content)
                file.flush()
                file.truncate()
                file.flush()
            except Exception:
                try:
                    file.seek(0)
                    file.write(content)
                    file.flush()
                    file.truncate()
                    file.flush()
                except Exception as error:
                    raise RuntimeError(
                        "File editing failed and restoring the original content also failed."
                    ) from error
                raise

        return FileEditResult(resolved_path)

    @staticmethod
    def _format_result(result: FileEditResult) -> str:
        return f"Path: {result.path}\nStatus: edited"

    def edit_file(
        self,
        path: str,
        old_text: str,
        new_text: str,
        encoding: str = "utf-8",
    ) -> str:
        """
        Replace a single exact occurrence of text in an existing file.

        Args:
            path: Absolute path of a text file inside the project and outside excluded directories; symbolic, junction, and hard links are rejected.
            old_text: Non-empty text that must occur at exactly one position, counting overlapping matches; case, whitespace, and line endings must match.
            new_text: Different text to insert exactly as provided; an empty string removes the matched text.
            encoding: Text encoding used to read and write the file; defaults to utf-8.

        Returns:
            The resolved path and edit status.
        """

        return self._format_result(self._edit(Path(path), old_text, new_text, encoding))
