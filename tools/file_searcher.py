from dataclasses import dataclass
from pathlib import Path
from re import IGNORECASE, compile, escape

from settings import settings

from .utility import is_hidden_path
from .validate import (
    validate_absolute_path,
    validate_directory_path,
    validate_non_excluded_project_path,
    validate_project_path,
)


@dataclass(frozen=True, slots=True)
class FileSearchLine:
    line_number: int
    line: str


@dataclass(frozen=True, slots=True)
class FileSearchMatch:
    path: Path
    line_number: int
    context: tuple[FileSearchLine, ...]


@dataclass(frozen=True, slots=True)
class FileSearchResult:
    path: Path
    query: str
    matches: tuple[FileSearchMatch, ...]
    searched_file_count: int
    matched_file_count: int
    skipped_path_count: int
    limit_reached: bool


class FileSearcher:
    @staticmethod
    def _matches_file_pattern(path: Path, root: Path, patterns: tuple[str, ...]) -> bool:
        relative_path = path.relative_to(root)
        return not patterns or any(
            relative_path.full_match(pattern) if "/" in pattern else relative_path.match(pattern)
            for pattern in patterns
        )

    @staticmethod
    def _shorten_line(
        line: str, match_start: int, match_end: int, max_line_length: int | None
    ) -> str:
        line = line.rstrip("\r\n")
        if max_line_length is None or len(line) <= max_line_length:
            return line
        match_length = match_end - match_start
        start = max(0, match_start - max(0, max_line_length - match_length) // 2)
        start = min(start, len(line) - max_line_length)
        end = start + max_line_length
        return f"{'…' if start else ''}{line[start:end]}{'…' if end < len(line) else ''}"

    @staticmethod
    def _shorten_context_line(line: str, max_line_length: int | None) -> str:
        line = line.rstrip("\r\n")
        if max_line_length is None or len(line) <= max_line_length:
            return line
        return f"{line[:max_line_length]}…"

    @classmethod
    def _search(
        cls,
        path: Path,
        query: str,
        use_regex: bool,
        case_sensitive: bool,
        file_patterns: list[str] | None,
        include_hidden: bool,
        excluded_names: list[str] | None,
        max_results: int | None,
        max_line_length: int | None,
        encoding: str,
    ) -> FileSearchResult:
        validate_absolute_path(path)
        if not query:
            raise ValueError("query must not be empty.")
        if max_results is not None and max_results < 1:
            raise ValueError("max_results must be positive.")
        if max_line_length is not None and max_line_length < 1:
            raise ValueError("max_line_length must be positive.")

        patterns = tuple(file_patterns or ())

        resolved_path = path.resolve(strict=True)
        validate_project_path(resolved_path)
        validate_non_excluded_project_path(resolved_path)
        validate_directory_path(resolved_path)

        pattern = compile(
            query if use_regex else escape(query), 0 if case_sensitive else IGNORECASE
        )
        excluded_name_set = frozenset(excluded_names or ())
        excluded_directories = settings.excluded_project_directories

        matches: list[FileSearchMatch] = []
        searched_file_count = 0
        matched_file_count = 0
        skipped_path_count = 0

        def _search_file(file_path: Path) -> list[FileSearchMatch] | None:
            try:
                with file_path.open("r", encoding=encoding, newline="") as file:
                    lines = file.readlines()
            except OSError, UnicodeError:
                return None

            found: list[FileSearchMatch] = []
            for index, line in enumerate(lines):
                if max_results is not None and len(matches) + len(found) >= max_results:
                    break

                match = pattern.search(line)
                if match is None:
                    continue

                context: list[FileSearchLine] = []
                for context_index in range(max(0, index - 1), min(len(lines), index + 2)):
                    context_line = lines[context_index]
                    if context_index == index:
                        text = cls._shorten_line(
                            context_line,
                            match.start(),
                            match.end(),
                            max_line_length,
                        )
                    else:
                        text = cls._shorten_context_line(
                            context_line,
                            max_line_length,
                        )
                    context.append(FileSearchLine(context_index + 1, text))

                found.append(FileSearchMatch(file_path, index + 1, tuple(context)))

            return found

        def _visit(directory: Path) -> None:
            nonlocal searched_file_count, matched_file_count, skipped_path_count

            try:
                entries = sorted(
                    directory.iterdir(),
                    key=lambda entry: (entry.name.casefold(), entry.name),
                )
            except OSError:
                skipped_path_count += 1
                return

            for entry in entries:
                if max_results is not None and len(matches) >= max_results:
                    return

                try:
                    if (
                        entry in excluded_directories
                        or entry.name in excluded_name_set
                        or (not include_hidden and is_hidden_path(entry))
                        or entry.is_symlink()
                        or entry.is_junction()
                    ):
                        continue

                    if entry.is_dir():
                        _visit(entry)
                    elif entry.is_file() and cls._matches_file_pattern(
                        entry, resolved_path, patterns
                    ):
                        searched_file_count += 1
                        found = _search_file(entry)

                        if found is None:
                            skipped_path_count += 1
                        elif found:
                            matches.extend(found)
                            matched_file_count += 1

                except OSError:
                    skipped_path_count += 1

        _visit(resolved_path)

        return FileSearchResult(
            resolved_path,
            query,
            tuple(matches),
            searched_file_count,
            matched_file_count,
            skipped_path_count,
            max_results is not None and len(matches) >= max_results,
        )

    @staticmethod
    def _format_result(result: FileSearchResult) -> str:
        header = (
            f"Path: {result.path}\n"
            f"Query: {result.query}\n"
            f"Matches: {len(result.matches)}\n"
            f"Matched files: {result.matched_file_count}\n"
            f"Searched files: {result.searched_file_count}\n"
            f"Skipped paths: {result.skipped_path_count}\n"
            f"Limit reached: {'yes' if result.limit_reached else 'no'}"
        )

        def _format_match(match: FileSearchMatch) -> str:
            last_line = match.context[-1].line_number
            line_number_width = len(str(last_line))
            lines = "\n".join(
                f"{'>' if line.line_number == match.line_number else ' '} "
                f"{line.line_number:>{line_number_width}}|{line.line}"
                for line in match.context
            )
            return f"{match.path}:{match.line_number}\n{lines}"

        content = "\n\n".join(_format_match(match) for match in result.matches)
        return f"{header}\nResults:\n{content}"

    @classmethod
    def search_files(
        cls,
        path: str,
        query: str,
        use_regex: bool = False,
        case_sensitive: bool = False,
        file_patterns: list[str] | None = None,
        include_hidden: bool = False,
        excluded_names: list[str] | None = None,
        max_results: int | None = None,
        max_line_length: int | None = None,
        encoding: str = "utf-8",
    ) -> str:
        """
        Search text recursively inside files without following links.
        Configured project directories and their contents are always omitted.

        Args:
            path: Absolute path of a directory inside the project.
            query: Literal text or regular expression to search for; must not be empty.
            use_regex: Whether query is a Python regular expression; defaults to False.
            case_sensitive: Whether letter case must match; defaults to False.
            file_patterns: Optional glob patterns for relative file paths, such as ["*.py", "src/**/*.ts"].
            include_hidden: Whether to search hidden files and directories; defaults to False.
            excluded_names: Exact file or directory names to omit at every depth; defaults to None.
            max_results: Maximum matching lines to return; None means unlimited; defaults to None.
            max_line_length: Maximum original characters per displayed line; None means unlimited; defaults to None.
            encoding: Text encoding used to read files; defaults to utf-8.

        Returns:
            Search statistics and matching lines with absolute paths and line numbers.
        """

        return cls._format_result(
            cls._search(
                Path(path),
                query,
                use_regex,
                case_sensitive,
                file_patterns,
                include_hidden,
                excluded_names,
                max_results,
                max_line_length,
                encoding,
            )
        )
