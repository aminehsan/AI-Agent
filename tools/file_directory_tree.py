from dataclasses import dataclass
from pathlib import Path

from settings import settings

from .utility import is_hidden_path, is_linked_project_path, resolve_project_path
from .validate import validate_directory_path


@dataclass(frozen=True, slots=True)
class FileDirectoryTreeResult:
    path: Path
    is_linked: bool
    tree_lines: tuple[str, ...]
    link_count: int
    directory_count: int
    file_count: int
    skipped_path_count: int


class FileDirectoryTree:
    @staticmethod
    def _build(
        path: Path,
        max_depth: int | None,
        include_hidden: bool,
        excluded_names: list[str] | None,
    ) -> FileDirectoryTreeResult:
        if max_depth is not None and max_depth < 1:
            raise ValueError("max_depth must be greater than or equal to 1.")
        is_linked = is_linked_project_path(path)
        resolved_path = resolve_project_path(path)
        validate_directory_path(resolved_path)

        excluded_name_set = frozenset(excluded_names or ())
        tree_lines = [f"{path.name}/" if path.name else str(path)]
        link_count = 0
        directory_count = 0
        file_count = 0
        skipped_path_count = 0

        def _visit(directory: Path, prefix: str, depth: int) -> None:
            nonlocal link_count, directory_count, file_count, skipped_path_count
            entries = []
            try:
                for entry in directory.iterdir():
                    try:
                        if (
                            entry in settings.excluded_project_directories
                            or entry.name in excluded_name_set
                            or (not include_hidden and is_hidden_path(entry))
                        ):
                            continue
                        is_link = entry.is_symlink() or entry.is_junction()
                        entries.append((entry, is_link, not is_link and entry.is_dir()))
                    except OSError:
                        skipped_path_count += 1
            except OSError:
                if depth == 1:
                    raise
                skipped_path_count += 1
                tree_lines.append(f"{prefix}└── (unreadable)")
                return
            entries.sort(
                key=lambda item: (
                    not item[2],
                    item[0].name.casefold(),
                    item[0].name,
                )
            )

            for index, (entry, is_link, is_directory) in enumerate(entries):
                is_last = index == len(entries) - 1
                connector = "└── " if is_last else "├── "
                child_prefix = prefix + ("    " if is_last else "│   ")
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
            path,
            is_linked,
            tuple(tree_lines),
            link_count,
            directory_count,
            file_count,
            skipped_path_count,
        )

    @staticmethod
    def _format_result(result: FileDirectoryTreeResult) -> str:
        formatted_tree = "\n".join(result.tree_lines)
        link_status = "Link: yes\n" if result.is_linked else ""
        return (
            f"Path: {result.path}\n"
            f"{link_status}"
            f"Links: {result.link_count}\n"
            f"Directories: {result.directory_count}\n"
            f"Files: {result.file_count}\n"
            f"Skipped paths: {result.skipped_path_count}\n"
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
        Unreadable child paths are skipped and counted; an unreadable root raises an error.

        Args:
            path: Absolute path of a directory inside the project.
            max_depth: Maximum depth below the root; null applies no limit; defaults to None.
            include_hidden: Whether to include hidden files and directories; defaults to False.
            excluded_names: Exact file or directory names to omit at every depth; defaults to None.

        Returns:
            The requested path, formatted tree, displayed entry counts, and skipped path count.
        """

        return self._format_result(
            self._build(
                Path(path),
                max_depth,
                include_hidden,
                excluded_names,
            )
        )
