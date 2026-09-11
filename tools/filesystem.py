from __future__ import annotations
import json
from typing import Annotated, Literal
from agents import function_tool
from pydantic import BaseModel, ConfigDict, Field
from .executor import execute_command
from .commands import FilesystemRequest, build_filesystem_command
from .models import EnvironmentVariable
from .environment import (
    get_runtime_environment,
    resolve_command_path,
    resolve_working_directory,
)


class _FilesystemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: int = Field(description="Current in-progress plan step.")
    purpose: str = Field(description="Why this single execution is needed now.")
    expected_result: str = Field(
        description="Concrete evidence expected from this execution."
    )
    path: str = Field(description="Target path, relative to cwd or absolute.")
    cwd: str | None = Field(
        default=None,
        description="Process working directory. Null uses PROJECT_ROOT.",
    )
    environment: list[EnvironmentVariable] | None = Field(
        default=None,
        description="Environment-variable overrides for this process.",
    )


class InspectInput(_FilesystemInput):
    action: Literal["inspect"] = "inspect"
    view: Literal["auto", "content", "children", "metadata"] = "auto"
    content_format: Literal["text", "base64"] = "text"
    recursive: bool = False


class WriteInput(_FilesystemInput):
    action: Literal["write"] = "write"
    entry_type: Literal["file", "directory"] = "file"
    content: str | None = Field(
        default=None,
        description="Complete UTF-8 text or base64 payload. Null is valid only for a directory.",
    )
    content_format: Literal["text", "base64"] = "text"


class RemoveInput(_FilesystemInput):
    action: Literal["remove"] = "remove"


class TransferInput(_FilesystemInput):
    action: Literal["transfer"] = "transfer"
    destination: str = Field(
        description="Destination path, relative to cwd or absolute."
    )
    transfer_mode: Literal["copy", "move"] = "copy"


class SearchInput(_FilesystemInput):
    action: Literal["search"] = "search"
    query: str = Field(description="Literal text or regular expression to search for.")
    search_target: Literal["name", "content", "both"] = "content"
    pattern_type: Literal["literal", "regex"] = "literal"
    case_sensitive: bool = False
    recursive: bool = True


FilesystemInput = Annotated[
    InspectInput | WriteInput | RemoveInput | TransferInput | SearchInput,
    Field(discriminator="action"),
]


@function_tool
async def filesystem(request: FilesystemInput) -> str:
    """Generate and execute one standard filesystem command for the detected operating system.

    Prefer this tool for common file work so shell syntax is deterministic. It supports five
    actions: inspect reads a file, lists a directory, or returns metadata; write creates or fully
    replaces a UTF-8/base64 file or creates a directory; remove recursively deletes a path;
    transfer copies or moves/renames a path; search finds path names, file contents, or both using
    literal or regular-expression matching. Every call requires the current plan step, a purpose,
    and an expected result. Paths and cwd may be relative or absolute. There is no path boundary,
    approval, timeout, or output limit. The generated command and full result are returned.

    Args:
        request: Action-specific filesystem request. Supply only the fields in the selected action.
    """

    arguments = request.model_dump()
    environment_overrides = {
        item.name: item.value for item in request.environment or []
    }
    try:
        if not request.path.strip():
            raise ValueError("path cannot be empty.")
        if isinstance(request, WriteInput):
            if request.entry_type == "file" and request.content is None:
                raise ValueError("content is required when writing a file.")
        if isinstance(request, SearchInput) and not request.query:
            raise ValueError("query cannot be empty.")
        working_directory = resolve_working_directory(request.cwd)
        source_path = resolve_command_path(request.path, working_directory)
        destination_path = (
            resolve_command_path(request.destination, working_directory)
            if isinstance(request, TransferInput)
            else None
        )
        command_request = FilesystemRequest(
            action=request.action,
            path=source_path,
            view=request.view if isinstance(request, InspectInput) else "auto",
            content=request.content if isinstance(request, WriteInput) else None,
            content_format=(
                request.content_format
                if isinstance(request, (InspectInput, WriteInput))
                else "text"
            ),
            entry_type=(
                request.entry_type if isinstance(request, WriteInput) else "file"
            ),
            recursive=(
                request.recursive
                if isinstance(request, (InspectInput, SearchInput))
                else False
            ),
            destination=destination_path,
            transfer_mode=(
                request.transfer_mode if isinstance(request, TransferInput) else "copy"
            ),
            query=request.query if isinstance(request, SearchInput) else None,
            search_target=(
                request.search_target if isinstance(request, SearchInput) else "content"
            ),
            pattern_type=(
                request.pattern_type if isinstance(request, SearchInput) else "literal"
            ),
            case_sensitive=(
                request.case_sensitive if isinstance(request, SearchInput) else False
            ),
        )
        spec = build_filesystem_command(get_runtime_environment(), command_request)
        result = await execute_command(
            step_id=request.step_id,
            tool_name="filesystem",
            action=request.action,
            purpose=request.purpose,
            expected_result=request.expected_result,
            command=spec.command,
            cwd=str(working_directory),
            stdin=spec.stdin,
            environment_overrides=environment_overrides,
            tool_arguments=arguments,
        )
    except Exception as exc:
        result = {
            "ok": False,
            "stage": "command_generation",
            "error": f"{type(exc).__name__}: {exc}",
            "arguments": arguments,
        }
    return json.dumps(result, ensure_ascii=False, indent=2)
