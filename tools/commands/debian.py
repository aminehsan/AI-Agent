from __future__ import annotations
import shlex
from .base import CommandSpec, FilesystemRequest


def _quote(value: object) -> str:
    return shlex.quote(str(value))


def _children(request: FilesystemRequest) -> str:
    path = _quote(request.path)
    if request.recursive:
        return f"find {path} -mindepth 1 -print"
    return f"find {path} -mindepth 1 -maxdepth 1 -print"


def _content(request: FilesystemRequest) -> str:
    path = _quote(request.path)
    if request.content_format == "base64":
        return f"base64 {path}"
    return f"cat -- {path}"


def _inspect(request: FilesystemRequest) -> CommandSpec:
    path = _quote(request.path)
    if request.view == "children":
        return CommandSpec(_children(request))
    if request.view == "content":
        return CommandSpec(_content(request))
    if request.view == "metadata":
        return CommandSpec(f"stat -- {path}")
    return CommandSpec(
        f"if [ -d {path} ]; then {_children(request)}; "
        f"elif [ -f {path} ]; then {_content(request)}; "
        f"else printf 'Path not found: %s\\n' {path} >&2; exit 1; fi"
    )


def _write(request: FilesystemRequest) -> CommandSpec:
    path = _quote(request.path)
    if request.entry_type == "directory":
        return CommandSpec(f"mkdir -p -- {path}")
    parent = _quote(request.path.parent)
    if request.content_format == "base64":
        command = f"mkdir -p -- {parent} && base64 --decode > {path}"
    else:
        command = f"mkdir -p -- {parent} && cat > {path}"
    return CommandSpec(command, request.content or "")


def _remove(request: FilesystemRequest) -> CommandSpec:
    return CommandSpec(f"rm -rf -- {_quote(request.path)}")


def _transfer(request: FilesystemRequest) -> CommandSpec:
    assert request.destination is not None
    source = _quote(request.path)
    destination = _quote(request.destination)
    parent = _quote(request.destination.parent)
    command = "cp -R" if request.transfer_mode == "copy" else "mv -f"
    return CommandSpec(f"mkdir -p -- {parent} && {command} -- {source} {destination}")


def _grep_flags(request: FilesystemRequest) -> str:
    flags = ["-F" if request.pattern_type == "literal" else "-E"]
    if not request.case_sensitive:
        flags.append("-i")
    return " ".join(flags)


def _name_search(request: FilesystemRequest) -> str:
    assert request.query is not None
    depth = "" if request.recursive else " -maxdepth 1"
    return (
        f"find {_quote(request.path)}{depth} -mindepth 1 -print | "
        f"grep {_grep_flags(request)} -- {_quote(request.query)}"
    )


def _content_search(request: FilesystemRequest) -> str:
    assert request.query is not None
    recursive = "-R " if request.recursive else ""
    return (
        f"grep {recursive}-n {_grep_flags(request)} -- "
        f"{_quote(request.query)} {_quote(request.path)}"
    )


def _search(request: FilesystemRequest) -> CommandSpec:
    if request.search_target == "name":
        return CommandSpec(_name_search(request))
    if request.search_target == "content":
        return CommandSpec(_content_search(request))
    return CommandSpec(
        "printf '%s\\n' '--- name matches ---'; "
        + _name_search(request)
        + "; printf '%s\\n' '--- content matches ---'; "
        + _content_search(request)
    )


def build_command(request: FilesystemRequest) -> CommandSpec:
    builders = {
        "inspect": _inspect,
        "write": _write,
        "remove": _remove,
        "transfer": _transfer,
        "search": _search,
    }
    return builders[request.action](request)
