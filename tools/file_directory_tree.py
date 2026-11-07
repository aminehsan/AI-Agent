from dataclasses import dataclass
from pathlib import Path

from .utility import format_path, resolve_linked_project_path, should_skip_entry
from .validate import validate_directory_path, validate_max_depth


@dataclass(frozen=True, slots=True)
class _FileDirectoryTreeResult:
    path: Path
    is_linked: bool
    tree_lines: tuple[str, ...]
    link_count: int
    directory_count: int
    file_count: int
    skipped_path_count: int


class FileDirectoryTree:
    @classmethod
    def _visit(
        cls,
        directory: Path,
        prefix: str,
        depth: int,
        max_depth: int | None,
        include_hidden: bool,
        excluded_names: frozenset[str],
        tree_lines: list[str],
    ) -> tuple[int, int, int, int]:
        link_count = 0
        directory_count = 0
        file_count = 0
        skipped_path_count = 0
        entries = []
        try:
            for entry in directory.iterdir():
                try:
                    if should_skip_entry(entry, excluded_names, include_hidden):
                        continue
                    is_link = entry.is_symlink() or entry.is_junction()
                    entries.append((entry, is_link, not is_link and entry.is_dir()))
                except OSError:
                    skipped_path_count += 1
        except OSError:
            if depth == 1:
                raise
            tree_lines.append(f"{prefix}└── (unreadable)")
            return 0, 0, 0, skipped_path_count + 1
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
                child_links, child_directories, child_files, child_skipped = cls._visit(
                    entry,
                    child_prefix,
                    depth + 1,
                    max_depth,
                    include_hidden,
                    excluded_names,
                    tree_lines,
                )
                link_count += child_links
                directory_count += child_directories
                file_count += child_files
                skipped_path_count += child_skipped

        return link_count, directory_count, file_count, skipped_path_count

    @classmethod
    def _build(
        cls,
        path: Path,
        max_depth: int | None,
        include_hidden: bool,
        excluded_names: list[str] | None,
    ) -> _FileDirectoryTreeResult:
        validate_max_depth(max_depth)
        resolved_path, is_linked = resolve_linked_project_path(path)
        validate_directory_path(resolved_path)

        tree_lines = [f"{path.name}/" if path.name else str(path)]
        excluded_name_set = frozenset(excluded_names or ())
        link_count, directory_count, file_count, skipped_path_count = cls._visit(
            resolved_path, "", 1, max_depth, include_hidden, excluded_name_set, tree_lines
        )
        if len(tree_lines) == 1:
            tree_lines.append("└── (no visible entries)")

        return _FileDirectoryTreeResult(
            path,
            is_linked,
            tuple(tree_lines),
            link_count,
            directory_count,
            file_count,
            skipped_path_count,
        )

    @staticmethod
    def _format_result(result: _FileDirectoryTreeResult) -> str:
        formatted_tree = "\n".join(result.tree_lines)
        return (
            f"{format_path(result.path, result.is_linked)}\n"
            f"Links: {result.link_count}\n"
            f"Directories: {result.directory_count}\n"
            f"Files: {result.file_count}\n"
            f"Skipped paths: {result.skipped_path_count}\n"
            f"Tree:\n{formatted_tree}"
        )

    @classmethod
    def list_file_directory(
        cls,
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

        return cls._format_result(
            cls._build(
                Path(path),
                max_depth,
                include_hidden,
                excluded_names,
            )
        )
