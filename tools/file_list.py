from dataclasses import dataclass
from os import name as os_name
from pathlib import Path
from stat import FILE_ATTRIBUTE_HIDDEN


@dataclass(frozen=True, slots=True)
class Result:
    path: Path
    lines: tuple[str, ...]
    link_count: int
    directory_count: int
    file_count: int


class FileList:
    @staticmethod
    def _is_hidden(path: Path) -> bool:
        if path.name.startswith("."):
            return True
        if os_name == "nt":
            return bool(path.stat(follow_symlinks=False).st_file_attributes & FILE_ATTRIBUTE_HIDDEN)
        return False

    @staticmethod
    def _build(
        path: Path,
        max_depth: int | None,
        include_hidden: bool,
        excluded_names: list[str] | None,
    ) -> Result:
        if not path.is_absolute():
            raise ValueError("Directory path must be absolute.")
        if max_depth is not None and max_depth < 1:
            raise ValueError("max_depth must be greater than or equal to 1.")
        try:
            resolved_path = path.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise ValueError(f"Cannot resolve directory path: {path}") from error
        if not resolved_path.is_dir():
            raise ValueError(f"Path is not a directory: {resolved_path}")

        excluded = frozenset(excluded_names or ())
        lines = [f"{resolved_path.name}/" if resolved_path.name else str(resolved_path)]
        link_count = 0
        directory_count = 0
        file_count = 0

        def visit(directory: Path, prefix: str, depth: int) -> None:
            nonlocal link_count, directory_count, file_count
            entries = [
                entry
                for entry in directory.iterdir()
                if entry.name not in excluded and (include_hidden or not FileList._is_hidden(entry))
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
                lines.append(f"{prefix}{connector}{label}")
                if is_directory and (max_depth is None or depth < max_depth):
                    visit(entry, child_prefix, depth + 1)

        visit(resolved_path, "", 1)
        if len(lines) == 1:
            lines.append("└── (no visible entries)")

        return Result(
            resolved_path,
            tuple(lines),
            link_count,
            directory_count,
            file_count,
        )

    @staticmethod
    def _format(result: Result) -> dict[str, str | int]:
        return {
            "path": str(result.path),
            "links": result.link_count,
            "directories": result.directory_count,
            "files": result.file_count,
            "tree": "\n".join(result.lines),
        }

    def show_files_and_directories(
        self,
        path: str,
        max_depth: int | None = None,
        include_hidden: bool = False,
        excluded_names: list[str] | None = None,
    ) -> dict[str, str | int]:
        """
        List files and directories as a deterministic tree without following links.

        Args:
            path: Absolute filesystem path of the directory to inspect.
            max_depth: Maximum depth below the root; null applies no limit; defaults to None.
            include_hidden: Whether to include hidden files and directories; defaults to False.
            excluded_names: Exact file or directory names to omit at every depth; defaults to None.

        Returns:
            The resolved path, formatted tree, and displayed entry counts.
        """

        return self._format(
            self._build(
                Path(path),
                max_depth,
                include_hidden,
                excluded_names,
            )
        )
