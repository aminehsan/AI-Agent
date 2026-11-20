from dataclasses import dataclass
from pathlib import Path

from .utility import format_path, is_windows_os, resolve_linked_project_path, should_skip_entry
from .validate import validate_directory_path, validate_search_options


@dataclass(frozen=True, slots=True)
class _PathMatch:
    relative_path: Path
    kind: str


@dataclass(frozen=True, slots=True)
class _PathFindResult:
    path: Path
    is_linked: bool
    query: str
    matches: tuple[_PathMatch, ...]
    skipped_path_count: int
    limit_reached: bool


@dataclass(frozen=True, slots=True)
class _PathFindOptions:
    root: Path
    query: str
    use_glob: bool
    match_relative_path: bool
    directories_only: bool
    case_sensitive: bool
    include_hidden: bool
    excluded_names: frozenset[str]
    max_results: int | None


class PathFinder:
    @classmethod
    def _visit(cls, directory: Path, options: _PathFindOptions, matches: list[_PathMatch]) -> int:
        try:
            entries = sorted(
                directory.iterdir(), key=lambda entry: (entry.name.casefold(), entry.name)
            )
        except OSError:
            if directory == options.root:
                raise
            return 1

        skipped_path_count = 0

        for entry in entries:
            if options.max_results is not None and len(matches) >= options.max_results:
                break

            try:
                if should_skip_entry(entry, options.excluded_names, options.include_hidden):
                    continue

                is_link = entry.is_symlink() or entry.is_junction()
                is_directory = not is_link and entry.is_dir()
                relative_path = entry.relative_to(options.root)

                if options.use_glob:
                    candidate = relative_path if options.match_relative_path else Path(entry.name)
                    is_match = candidate.full_match(
                        options.query, case_sensitive=options.case_sensitive
                    )
                else:
                    name = entry.name if options.case_sensitive else entry.name.casefold()
                    is_match = name == options.query

                if is_match and (not options.directories_only or is_directory):
                    if is_link:
                        kind = "Link"
                    elif is_directory:
                        kind = "Directory"
                    elif entry.is_file():
                        kind = "File"
                    else:
                        continue

                    matches.append(_PathMatch(relative_path, kind))
                    if options.max_results is not None and len(matches) >= options.max_results:
                        break

                if is_directory:
                    skipped_path_count += cls._visit(entry, options, matches)

            except OSError:
                skipped_path_count += 1

        return skipped_path_count

    @classmethod
    def _find(
        cls,
        path: Path,
        query: str,
        use_glob: bool,
        case_sensitive: bool,
        include_hidden: bool,
        excluded_names: list[str] | None,
        max_results: int | None,
    ) -> _PathFindResult:
        validate_search_options(query, max_results)

        resolved_path, is_linked = resolve_linked_project_path(path)
        validate_directory_path(resolved_path)

        separators = ("/", "\\") if is_windows_os() else ("/",)
        options = _PathFindOptions(
            root=resolved_path,
            query=query if use_glob or case_sensitive else query.casefold(),
            use_glob=use_glob,
            match_relative_path=any(separator in query for separator in separators),
            directories_only=use_glob and query.endswith(separators),
            case_sensitive=case_sensitive,
            include_hidden=include_hidden,
            excluded_names=frozenset(excluded_names or ()),
            max_results=max_results,
        )

        matches: list[_PathMatch] = []
        skipped_path_count = cls._visit(resolved_path, options, matches)

        return _PathFindResult(
            path,
            is_linked,
            query,
            tuple(matches),
            skipped_path_count,
            max_results is not None and len(matches) >= max_results,
        )

    @staticmethod
    def _format_result(result: _PathFindResult) -> str:
        displayed_query = result.query.replace("\r", "\\r").replace("\n", "\\n")
        header = (
            f"{format_path(result.path, result.is_linked)}\n"
            f"Query: {displayed_query}\n"
            f"Matches: {len(result.matches)}\n"
            f"Skipped paths: {result.skipped_path_count}\n"
            f"Limit reached: {'yes' if result.limit_reached else 'no'}"
        )
        if not result.matches:
            return f"{header}\nResults: No matches found"

        content = "\n".join(
            f"{match.kind}: {result.path / match.relative_path}" for match in result.matches
        )
        return f"{header}\nResults:\n{content}"

    @classmethod
    def find_paths(
        cls,
        path: str,
        query: str,
        use_glob: bool = False,
        case_sensitive: bool = False,
        include_hidden: bool = False,
        excluded_names: list[str] | None = None,
        max_results: int | None = None,
    ) -> str:
        """
        Find files and directories recursively by name or glob pattern without reading file contents.
        Matching symbolic links and junctions are reported as links and are never traversed.
        An explicitly supplied directory link may be searched if its target stays inside the project.
        Configured project directories and their contents are always omitted.
        Unreadable child paths are skipped and counted; an unreadable root raises an error.
        Args:
            path: Absolute path of the directory to search inside the project.
            query: Exact basename, or a glob pattern when use_glob is true. A glob without path separators, such as "*.py", matches names at any depth. A glob with separators, such as "src/**/*.py", matches paths relative to the search directory. On Windows, both slash styles are accepted. A trailing separator limits matches to directories. The query must not be empty.
            use_glob: Whether to interpret query as a glob pattern; defaults to False.
            case_sensitive: Whether letter case must match; defaults to False.
            include_hidden: Whether to include hidden files and directories; defaults to False.
            excluded_names: Exact entry names to omit at every depth; defaults to None.
            max_results: Maximum matches to return; None means unlimited; defaults to None.
        Returns:
            Matching absolute paths with entry types, match and skipped path counts, and limit status.
        """

        return cls._format_result(
            cls._find(
                Path(path),
                query,
                use_glob,
                case_sensitive,
                include_hidden,
                excluded_names,
                max_results,
            )
        )
