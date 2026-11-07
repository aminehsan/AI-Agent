from dataclasses import dataclass
from os import fstat
from pathlib import Path

from .utility import has_file_changed, is_linked_project_path, resolve_project_path
from .validate import validate_file_path


@dataclass(frozen=True, slots=True)
class FileEditResult:
    path: Path
    is_linked: bool


class FileEditor:
    @staticmethod
    def _edit(path: Path, old_text: str, new_text: str, encoding: str) -> FileEditResult:
        if not old_text:
            raise ValueError("old_text must not be empty.")
        if old_text == new_text:
            raise ValueError("new_text must differ from old_text.")

        is_linked = is_linked_project_path(path)
        resolved_path = resolve_project_path(path)
        validate_file_path(resolved_path)

        with resolved_path.open("r+", encoding=encoding, newline="") as file:
            original_stat = fstat(file.fileno())
            if original_stat.st_nlink != 1:
                raise ValueError("Editing a hard-linked file is not allowed.")
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
        link_status = "\nLink: yes" if result.is_linked else ""
        return f"Path: {result.path}{link_status}\nStatus: edited"

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
