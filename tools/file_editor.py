from dataclasses import dataclass
from os import fstat
from pathlib import Path

from .utility import format_path, has_file_changed, resolve_linked_project_path
from .validate import (
    validate_edit_text,
    validate_file_path,
    validate_not_hard_linked,
    validate_single_occurrence,
)


@dataclass(frozen=True, slots=True)
class FileEditResult:
    path: Path
    is_linked: bool


class FileEditor:
    @staticmethod
    def _edit(path: Path, old_text: str, new_text: str, encoding: str) -> FileEditResult:
        validate_edit_text(old_text, new_text)
        resolved_path, is_linked = resolve_linked_project_path(path)
        validate_file_path(resolved_path)

        with resolved_path.open("r+", encoding=encoding, newline="") as file:
            original_stat = fstat(file.fileno())
            validate_not_hard_linked(original_stat.st_nlink)
            content = file.read()
            validate_single_occurrence(content, old_text)

            updated_content = content.replace(old_text, new_text, 1)

            if has_file_changed(resolved_path, original_stat) or (
                fstat(file.fileno()).st_nlink != 1
            ):
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

        return FileEditResult(path, is_linked)

    @staticmethod
    def _format_result(result: FileEditResult) -> str:
        return f"{format_path(result.path, result.is_linked)}\nStatus: edited"

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
            path: Absolute path of a text file inside the project and outside excluded directories; linked targets must remain inside the project, and hard-linked files cannot be edited.
            old_text: Non-empty text that must occur at exactly one position, counting overlapping matches; case, whitespace, and line endings must match.
            new_text: Different text to insert exactly as provided; an empty string removes the matched text.
            encoding: Text encoding used to read and write the file; defaults to utf-8.

        Returns:
            The requested path and edit status.
        """

        return self._format_result(self._edit(Path(path), old_text, new_text, encoding))
