from pathlib import Path

from settings import settings


def validate_project_path(path: Path) -> None:
    project_root = settings.project_root
    if not path.is_relative_to(project_root):
        raise ValueError(f"Path must be inside project root: {project_root}, received: {path}")


def validate_non_project_root_path(path: Path) -> None:
    if path == settings.project_root:
        raise ValueError(f"Path must not be the project root: {path}")


def validate_absolute_path(path: Path) -> None:
    if not path.is_absolute():
        raise ValueError(f"Path must be absolute: {path}")


def validate_directory_parent_path(path: Path) -> None:
    if not path.is_dir():
        raise ValueError(f"Parent path must be directory: {path}")


def validate_directory_path(path: Path) -> None:
    if not path.is_dir():
        raise ValueError(f"Path must be directory: {path}")


def validate_file_path(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"Path must be file: {path}")


def validate_non_excluded_project_path(path: Path) -> None:
    directories = tuple(directory.resolve() for directory in settings.excluded_project_directories)
    if any(
        path.is_relative_to(directory)
        for directory in (*settings.excluded_project_directories, *directories)
    ):
        raise ValueError(f"Path must not be inside an excluded project directory: {path}")


def validate_logical_project_path(path: Path) -> None:
    validate_absolute_path(path)
    if ".." in path.parts:
        raise ValueError(f"Path must not contain '..': {path}")
    validate_project_path(path)
    validate_non_excluded_project_path(path)


def validate_max_depth(max_depth: int | None) -> None:
    if max_depth is not None and max_depth < 1:
        raise ValueError("max_depth must be greater than or equal to 1.")


def validate_line_range(start_line: int, end_line: int | None) -> None:
    if start_line < 1:
        raise ValueError("start_line must be greater than or equal to 1.")
    if end_line is not None and end_line < start_line:
        raise ValueError("end_line must be greater than or equal to start_line.")


def validate_search_options(
    query: str, max_results: int | None, max_line_length: int | None
) -> None:
    if not query:
        raise ValueError("query must not be empty.")
    if max_results is not None and max_results < 1:
        raise ValueError("max_results must be positive.")
    if max_line_length is not None and max_line_length < 1:
        raise ValueError("max_line_length must be positive.")


def validate_edit_text(old_text: str, new_text: str) -> None:
    if not old_text:
        raise ValueError("old_text must not be empty.")
    if old_text == new_text:
        raise ValueError("new_text must differ from old_text.")


def validate_single_occurrence(content: str, old_text: str) -> None:
    match_count = 0
    match_index = content.find(old_text)
    while match_index != -1:
        match_count += 1
        match_index = content.find(old_text, match_index + 1)
    if match_count != 1:
        raise ValueError(f"old_text must occur exactly once; found {match_count} occurrences.")


def validate_not_hard_linked(link_count: int) -> None:
    if link_count != 1:
        raise ValueError("Editing a hard-linked file is not allowed.")
