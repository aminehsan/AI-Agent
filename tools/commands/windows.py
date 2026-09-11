from __future__ import annotations
from .base import CommandSpec, FilesystemRequest


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _path(value: object) -> str:
    return _quote(str(value))


def _children_command(request: FilesystemRequest) -> str:
    recurse = " -Recurse" if request.recursive else ""
    return (
        f"Get-ChildItem -LiteralPath {_path(request.path)} -Force{recurse} | "
        "Select-Object FullName, Length, LastWriteTime, Attributes | "
        "Format-Table -AutoSize | Out-String -Width 4096"
    )


def _content_command(request: FilesystemRequest) -> str:
    if request.content_format == "base64":
        return (
            "[Convert]::ToBase64String("
            f"[IO.File]::ReadAllBytes({_path(request.path)}))"
        )
    return f"Get-Content -Raw -LiteralPath {_path(request.path)} -Encoding UTF8"


def _inspect(request: FilesystemRequest) -> CommandSpec:
    if request.view == "children":
        return CommandSpec(_children_command(request))
    if request.view == "content":
        return CommandSpec(_content_command(request))
    if request.view == "metadata":
        return CommandSpec(
            f"Get-Item -LiteralPath {_path(request.path)} -Force | Format-List * | Out-String"
        )
    children = _children_command(request)
    content = _content_command(request)
    path = _path(request.path)
    command = (
        f"if (Test-Path -LiteralPath {path} -PathType Container) {{ {children} }} "
        f"elseif (Test-Path -LiteralPath {path} -PathType Leaf) {{ {content} }} "
        f"else {{ Write-Error ('Path not found: ' + {path}); exit 1 }}"
    )
    return CommandSpec(command)


def _write(request: FilesystemRequest) -> CommandSpec:
    path = _path(request.path)
    if request.entry_type == "directory":
        return CommandSpec(
            f"New-Item -ItemType Directory -Force -Path {path} | Out-String"
        )
    parent = _path(request.path.parent)
    prepare = f"New-Item -ItemType Directory -Force -Path {parent} | Out-Null; "
    if request.content_format == "base64":
        write = (
            "$agentContent = [Console]::In.ReadToEnd(); "
            f"[IO.File]::WriteAllBytes({path}, [Convert]::FromBase64String($agentContent))"
        )
    else:
        write = (
            "$agentContent = [Console]::In.ReadToEnd(); "
            f"[IO.File]::WriteAllText({path}, $agentContent, "
            "[Text.UTF8Encoding]::new($false))"
        )
    return CommandSpec(prepare + write, request.content or "")


def _remove(request: FilesystemRequest) -> CommandSpec:
    return CommandSpec(
        f"Remove-Item -LiteralPath {_path(request.path)} -Recurse -Force"
    )


def _transfer(request: FilesystemRequest) -> CommandSpec:
    assert request.destination is not None
    source = _path(request.path)
    destination = _path(request.destination)
    parent = _path(request.destination.parent)
    prepare = f"New-Item -ItemType Directory -Force -Path {parent} | Out-Null; "
    if request.transfer_mode == "copy":
        command = f"Copy-Item -LiteralPath {source} -Destination {destination} -Recurse -Force"
    else:
        command = f"Move-Item -LiteralPath {source} -Destination {destination} -Force"
    return CommandSpec(prepare + command)


def _name_search(request: FilesystemRequest) -> str:
    assert request.query is not None
    recurse = " -Recurse" if request.recursive else ""
    operator = "-cmatch" if request.case_sensitive else "-match"
    pattern = _quote(request.query)
    if request.pattern_type == "literal":
        pattern = f"[regex]::Escape({pattern})"
    return (
        f"Get-ChildItem -LiteralPath {_path(request.path)} -Force{recurse} | "
        f"Where-Object {{ $_.Name {operator} {pattern} }} | "
        "Select-Object -ExpandProperty FullName"
    )


def _content_search(request: FilesystemRequest) -> str:
    assert request.query is not None
    recurse = " -Recurse" if request.recursive else ""
    simple = " -SimpleMatch" if request.pattern_type == "literal" else ""
    case = " -CaseSensitive" if request.case_sensitive else ""
    return (
        f"Get-ChildItem -LiteralPath {_path(request.path)} -File -Force{recurse} | "
        f"Select-String -Pattern {_quote(request.query)}{simple}{case} | "
        "ForEach-Object { '{0}:{1}:{2}' -f $_.Path, $_.LineNumber, $_.Line }"
    )


def _search(request: FilesystemRequest) -> CommandSpec:
    if request.search_target == "name":
        return CommandSpec(_name_search(request))
    if request.search_target == "content":
        return CommandSpec(_content_search(request))
    return CommandSpec(
        "Write-Output '--- name matches ---'; "
        + _name_search(request)
        + "; Write-Output '--- content matches ---'; "
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
