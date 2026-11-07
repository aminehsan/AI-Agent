from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
from re import DOTALL, IGNORECASE, MULTILINE, compile, escape

from .utility import format_path, resolve_linked_project_path, should_skip_entry
from .validate import validate_directory_path, validate_search_options


@dataclass(frozen=True, slots=True)
class FileSearchLine:
    line_number: int
    line: str


@dataclass(frozen=True, slots=True)
class FileSearchMatch:
    path: Path
    start_line_number: int
    end_line_number: int
    context: tuple[FileSearchLine, ...]


@dataclass(frozen=True, slots=True)
class FileSearchResult:
    path: Path
    is_linked: bool
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
        match_start = max(0, min(len(line), match_start))
        match_end = max(match_start, min(len(line), match_end))
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

    def _search(
        self,
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
        validate_search_options(query, max_results, max_line_length)

        patterns = tuple(file_patterns or ())

        resolved_path, is_linked = resolve_linked_project_path(path, allow_external_link=True)
        validate_directory_path(resolved_path)

        flags = DOTALL | MULTILINE | (0 if case_sensitive else IGNORECASE)
        pattern = compile(query if use_regex else escape(query), flags)
        excluded_name_set = frozenset(excluded_names or ())
        matches: list[FileSearchMatch] = []
        searched_file_count = 0
        matched_file_count = 0
        skipped_path_count = 0

        def _search_file(file_path: Path) -> list[FileSearchMatch] | None:
            found: list[FileSearchMatch] = []
            display_path = path / file_path.relative_to(resolved_path)
            try:
                with file_path.open("r", encoding=encoding, newline="") as file:
                    content = file.read()

                lines = content.splitlines(keepends=True)

                line_starts = [0]
                for line in lines[:-1]:
                    line_starts.append(line_starts[-1] + len(line))

                for match in pattern.finditer(content):
                    start_offset, end_offset = match.span()
                    if start_offset == len(content) and (
                        not content or content[-1] in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"
                    ):
                        continue
                    start_line_number = bisect_right(line_starts, start_offset)
                    end_line_number = bisect_right(line_starts, max(start_offset, end_offset - 1))
                    context: list[FileSearchLine] = []

                    for line_number in range(
                        max(1, start_line_number - 1),
                        min(len(lines), end_line_number + 1) + 1,
                    ):
                        line = lines[line_number - 1]
                        if start_line_number <= line_number <= end_line_number:
                            line_offset = line_starts[line_number - 1]
                            displayed_line = self._shorten_line(
                                line,
                                start_offset - line_offset,
                                end_offset - line_offset,
                                max_line_length,
                            )
                        else:
                            displayed_line = self._shorten_context_line(line, max_line_length)
                        context.append(FileSearchLine(line_number, displayed_line))

                    found.append(
                        FileSearchMatch(
                            display_path, start_line_number, end_line_number, tuple(context)
                        )
                    )
                    if max_results is not None and len(matches) + len(found) >= max_results:
                        break
            except OSError, UnicodeError:
                return None
            return found

        def _visit(directory: Path) -> None:
            nonlocal searched_file_count, matched_file_count, skipped_path_count
            try:
                entries = sorted(
                    directory.iterdir(), key=lambda entry: (entry.name.casefold(), entry.name)
                )
            except OSError:
                if directory == resolved_path:
                    raise
                skipped_path_count += 1
                return

            for entry in entries:
                if max_results is not None and len(matches) >= max_results:
                    return
                try:
                    if should_skip_entry(entry, excluded_name_set, include_hidden):
                        continue
                    if entry.is_symlink() or entry.is_junction():
                        continue
                    if entry.is_dir():
                        _visit(entry)
                    elif entry.is_file() and self._matches_file_pattern(
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
            path,
            is_linked,
            query,
            tuple(matches),
            searched_file_count,
            matched_file_count,
            skipped_path_count,
            max_results is not None and len(matches) >= max_results,
        )

    @staticmethod
    def _format_result(result: FileSearchResult) -> str:
        displayed_query = result.query.replace("\r", "\\r").replace("\n", "\\n")
        header = (
            f"{format_path(result.path, result.is_linked)}\n"
            f"Query: {displayed_query}\n"
            f"Matches: {len(result.matches)}\n"
            f"Matched files: {result.matched_file_count}\n"
            f"Searched files: {result.searched_file_count}\n"
            f"Skipped paths: {result.skipped_path_count}\n"
            f"Limit reached: {'yes' if result.limit_reached else 'no'}"
        )
        if not result.matches:
            return f"{header}\nResults: No matches found"

        def _format_match(match: FileSearchMatch) -> str:
            last_line = match.context[-1].line_number
            line_number_width = len(str(last_line))
            lines = "\n".join(
                f"{'>' if match.start_line_number <= line.line_number <= match.end_line_number else ' '} "
                f"{line.line_number:>{line_number_width}}|{line.line}"
                for line in match.context
            )
            location = str(match.start_line_number)
            if match.end_line_number != match.start_line_number:
                location = f"{location}-{match.end_line_number}"
            return f"{match.path}:{location}\n{lines}"

        content = "\n\n".join(_format_match(match) for match in result.matches)

        return f"{header}\nResults:\n{content}"

    def search_files(
        self,
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
        Search text recursively without following links found during traversal.
        An explicitly supplied directory link may be searched.
        Literal and regex queries can match across lines; regex dots also match newlines.
        Configured project directories and their contents are always omitted.
        Unreadable child paths are skipped and counted; an unreadable root raises an error.

        Args:
            path: Absolute path of a directory inside the project; an explicitly supplied link may point outside it.
            query: Literal text or regular expression to search for; must not be empty.
            use_regex: Whether query is a Python regular expression; defaults to False.
            case_sensitive: Whether letter case must match; defaults to False.
            file_patterns: Optional glob patterns for relative file paths, such as ["*.py", "src/**/*.ts"].
            include_hidden: Whether to search hidden files and directories; defaults to False.
            excluded_names: Exact file or directory names to omit at every depth; defaults to None.
            max_results: Maximum matching occurrences to return; None means unlimited; defaults to None.
            max_line_length: Maximum original characters per displayed line; None means unlimited; defaults to None.
            encoding: Text encoding used to read files; defaults to utf-8.

        Returns:
            Search statistics and matching occurrences with absolute paths and line ranges.
        """

        return self._format_result(
            self._search(
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
