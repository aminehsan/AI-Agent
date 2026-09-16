from json import dumps
from pathlib import Path
from subprocess import run
from collections.abc import Callable
from agents import function_tool
from settings import settings


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


def _tool_result(tool: str, operation: Callable[[], object]) -> str:
    try:
        output = operation()
        return dumps(
            {"ok": True, "tool": tool, "output": output},
            ensure_ascii=False,
        )
    except Exception as exc:
        return dumps(
            {
                "ok": False,
                "tool": tool,
                "error": f"{type(exc).__name__}: {exc}",
            },
            ensure_ascii=False,
        )


@function_tool
def list_files() -> str:
    """List all accessible files under the configured project root."""
    return _tool_result("list_files", get_project_files)


@function_tool
def read_file(path: str) -> str:
    """Read a UTF-8 project file using a path relative to the project root."""

    def read() -> str:
        file_path = resolve_project_path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        return file_path.read_text(encoding="utf-8")

    return _tool_result("read_file", read)


@function_tool
def write_file(path: str, content: str) -> str:
    """Create or overwrite a UTF-8 project file."""

    def write() -> str:
        file_path = resolve_project_path(path)
        existed = file_path.exists()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"{'Updated' if existed else 'Created'}: {path}"

    return _tool_result("write_file", write)


@function_tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace one exact text occurrence in an existing UTF-8 project file."""

    def edit() -> str:
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

    return _tool_result("edit_file", edit)


@function_tool
def run_command(program: str, arguments: list[str]) -> str:
    """Run one program in the project root without a shell and return its result."""
    try:
        completed = run(
            [program, *arguments],
            cwd=settings.project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        return dumps(
            {
                "ok": completed.returncode == 0,
                "tool": "run_command",
                "program": program,
                "arguments": arguments,
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return dumps(
            {
                "ok": False,
                "tool": "run_command",
                "program": program,
                "arguments": arguments,
                "error": f"{type(exc).__name__}: {exc}",
            },
            ensure_ascii=False,
        )
