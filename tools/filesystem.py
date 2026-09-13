from pathlib import Path
from collections.abc import Callable
from agents import function_tool
from settings import settings
from plan.store import plan_store

IGNORED_DIRECTORIES = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    ".venv",
    settings.project_state_directory_name,
}


def resolve_project_path(relative_path: str) -> Path:
    if not relative_path.strip():
        raise ValueError("Path cannot be empty.")
    path = (settings.project_root / relative_path).resolve()
    if not path.is_relative_to(settings.project_root):
        raise ValueError("Path must stay inside the project root.")
    project_path = path.relative_to(settings.project_root)
    if any(part in IGNORED_DIRECTORIES for part in project_path.parts):
        raise PermissionError("Access to this directory is not allowed.")
    if project_path.name == ".env":
        raise PermissionError("Access to .env is not allowed.")
    return path


def get_project_files() -> list[str]:
    files = []
    for path in settings.project_root.rglob("*"):
        relative_path = path.relative_to(settings.project_root)
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRECTORIES for part in relative_path.parts):
            continue
        if relative_path.name == ".env":
            continue
        files.append(relative_path.as_posix())
    return sorted(files)


def read_project_file(path: str) -> str:
    file_path = resolve_project_path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    return file_path.read_text(encoding="utf-8")


def write_project_file(path: str, content: str) -> str:
    file_path = resolve_project_path(path)
    existed = file_path.exists()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    action = "Updated" if existed else "Created"
    return f"{action}: {path}"


def edit_project_file(path: str, old_text: str, new_text: str) -> str:
    file_path = resolve_project_path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    content = file_path.read_text(encoding="utf-8")
    occurrences = content.count(old_text)
    if occurrences == 0:
        raise ValueError("The requested text was not found.")
    if occurrences > 1:
        raise ValueError("The requested text occurs more than once.")
    file_path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
    return f"Updated: {path}"


def _execute_planned_tool(
    *,
    step_id: int,
    tool_name: str,
    action: str,
    purpose: str,
    expected_result: str,
    arguments: dict[str, str],
    operation: Callable[[], str],
) -> str:
    """Run one existing filesystem operation through the active plan gate."""
    reservation = plan_store.begin_execution(
        step_id=step_id,
        tool_name=tool_name,
        action=action,
        purpose=purpose,
        expected_result=expected_result,
        details={
            "tool": tool_name,
            "action": action,
            "purpose": purpose,
            "expected_result": expected_result,
            "arguments": arguments,
        },
    )

    try:
        output = operation()
    except Exception as exc:
        plan_store.finish_execution(
            step_id=step_id,
            attempt_number=reservation["attempt_number"],
            execution_id=reservation["execution_id"],
            result={
                "ok": False,
                "exit_code": 1,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        raise

    plan_store.finish_execution(
        step_id=step_id,
        attempt_number=reservation["attempt_number"],
        execution_id=reservation["execution_id"],
        result={"ok": True, "exit_code": 0, "output": output},
    )
    return output


@function_tool
def list_files(
    step_id: int,
    purpose: str,
    expected_result: str,
) -> str:
    """List project paths for the current in-progress plan step."""
    return _execute_planned_tool(
        step_id=step_id,
        tool_name="list_files",
        action="list",
        purpose=purpose,
        expected_result=expected_result,
        arguments={},
        operation=lambda: "\n".join(get_project_files()) or "No files found.",
    )


@function_tool
def read_file(
    step_id: int,
    purpose: str,
    expected_result: str,
    path: str,
) -> str:
    """Read a UTF-8 file for the current in-progress plan step."""
    return _execute_planned_tool(
        step_id=step_id,
        tool_name="read_file",
        action="read",
        purpose=purpose,
        expected_result=expected_result,
        arguments={"path": path},
        operation=lambda: read_project_file(path),
    )


@function_tool
def write_file(
    step_id: int,
    purpose: str,
    expected_result: str,
    path: str,
    content: str,
) -> str:
    """Create or overwrite a UTF-8 file for the current plan step."""
    return _execute_planned_tool(
        step_id=step_id,
        tool_name="write_file",
        action="write",
        purpose=purpose,
        expected_result=expected_result,
        arguments={"path": path, "content": content},
        operation=lambda: write_project_file(path, content),
    )


@function_tool
def edit_file(
    step_id: int,
    purpose: str,
    expected_result: str,
    path: str,
    old_text: str,
    new_text: str,
) -> str:
    """Replace one exact text occurrence for the current plan step."""
    return _execute_planned_tool(
        step_id=step_id,
        tool_name="edit_file",
        action="edit",
        purpose=purpose,
        expected_result=expected_result,
        arguments={"path": path, "old_text": old_text, "new_text": new_text},
        operation=lambda: edit_project_file(path, old_text, new_text),
    )
