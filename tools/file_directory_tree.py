from dataclasses import dataclass
from pathlib import Path

from settings import settings

from .utility import is_hidden_path
from .validate import (
    validate_absolute_path,
    validate_directory_path,
    validate_non_excluded_project_path,
    validate_project_path,
)


@dataclass(frozen=True, slots=True)
class FileDirectoryTreeResult:
    path: Path
    tree_lines: tuple[str, ...]
    link_count: int
    directory_count: int
    file_count: int


class FileDirectoryTree:
    def _build(
        self,
        path: Path,
        max_depth: int | None,
        include_hidden: bool,
        excluded_names: list[str] | None,
    ) -> FileDirectoryTreeResult:
        validate_absolute_path(path)
        if max_depth is not None and max_depth < 1:
            raise ValueError("max_depth must be greater than or equal to 1.")
        resolved_path = path.resolve(strict=True)
        validate_project_path(resolved_path)
        validate_non_excluded_project_path(resolved_path)
        validate_directory_path(resolved_path)

        excluded_name_set = frozenset(excluded_names or ())
        tree_lines = [f"{resolved_path.name}/" if resolved_path.name else str(resolved_path)]
        link_count = 0
        directory_count = 0
        file_count = 0

        def _visit(directory: Path, prefix: str, depth: int) -> None:
            nonlocal link_count, directory_count, file_count
            entries = [
                entry
                for entry in directory.iterdir()
                if entry not in settings.excluded_project_directories
                and entry.name not in excluded_name_set
                and (include_hidden or not is_hidden_path(entry))
            ]
            entries.sort(
                key=lambda entry: (
                    entry.is_symlink() or entry.is_junction() or not entry.is_dir(),
                    entry.name.casefold(),
                    entry.name,
                )
            )

            for index, entry in enumerate(entries):
                is_last = index == len(entries) - 1
                connector = "└── " if is_last else "├── "
                child_prefix = prefix + ("    " if is_last else "│   ")
                is_link = entry.is_symlink() or entry.is_junction()
                is_directory = not is_link and entry.is_dir()
                if is_link:
                    label = f"{entry.name}@"
                    link_count += 1
                elif is_directory:
                    label = f"{entry.name}/"
                    directory_count += 1
                    if max_depth is not None and depth >= max_depth:
                        label += " [depth limit]"
                else:
                    label = entry.name
                    file_count += 1
                tree_lines.append(f"{prefix}{connector}{label}")
                if is_directory and (max_depth is None or depth < max_depth):
                    _visit(entry, child_prefix, depth + 1)

        _visit(resolved_path, "", 1)
        if len(tree_lines) == 1:
            tree_lines.append("└── (no visible entries)")

        return FileDirectoryTreeResult(
            resolved_path,
            tuple(tree_lines),
            link_count,
            directory_count,
            file_count,
        )

    @staticmethod
    def _format_result(result: FileDirectoryTreeResult) -> str:
        formatted_tree = "\n".join(result.tree_lines)
        return (
            f"Path: {result.path}\n"
            f"Links: {result.link_count}\n"
            f"Directories: {result.directory_count}\n"
            f"Files: {result.file_count}\n"
            f"Tree:\n{formatted_tree}"
        )

    def list_file_directory(
        self,
        path: str,
        max_depth: int | None = None,
        include_hidden: bool = False,
        excluded_names: list[str] | None = None,
    ) -> str:
        """
        List files and directories as a deterministic tree without following links.
        Configured project directories and their contents are always omitted.

        Args:
            path: Absolute path of a directory inside the project.
            max_depth: Maximum depth below the root; null applies no limit; defaults to None.
            include_hidden: Whether to include hidden files and directories; defaults to False.
            excluded_names: Exact file or directory names to omit at every depth; defaults to None.

        Returns:
            The resolved path, formatted tree, and displayed entry counts.
        """

        return self._format_result(
            self._build(
                Path(path),
                max_depth,
                include_hidden,
                excluded_names,
            )
        )
