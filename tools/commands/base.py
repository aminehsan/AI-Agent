from __future__ import annotations
from pathlib import Path
from typing import Literal
from dataclasses import dataclass


FilesystemAction = Literal["inspect", "write", "remove", "transfer", "search"]
InspectView = Literal["auto", "content", "children", "metadata"]
ContentFormat = Literal["text", "base64"]
EntryType = Literal["file", "directory"]
TransferMode = Literal["copy", "move"]
SearchTarget = Literal["name", "content", "both"]
PatternType = Literal["literal", "regex"]


@dataclass(frozen=True)
class CommandSpec:
    command: str
    stdin: str | None = None


@dataclass(frozen=True)
class FilesystemRequest:
    action: FilesystemAction
    path: Path
    view: InspectView = "auto"
    content: str | None = None
    content_format: ContentFormat = "text"
    entry_type: EntryType = "file"
    recursive: bool = False
    destination: Path | None = None
    transfer_mode: TransferMode = "copy"
    query: str | None = None
    search_target: SearchTarget = "content"
    pattern_type: PatternType = "literal"
    case_sensitive: bool = False
