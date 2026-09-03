from pathlib import Path
from agents import function_tool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRECTORIES = {".git", ".idea", ".venv", ".vscode", "__pycache__"}


def get_project_files() -> list[str]:
    files = []
    for path in PROJECT_ROOT.rglob("*"):
        relative_path = path.relative_to(PROJECT_ROOT)
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRECTORIES for part in relative_path.parts):
            continue
        if relative_path.name == ".env":
            continue
        files.append(relative_path.as_posix())
    return sorted(files)


@function_tool
def list_files() -> str:
    """List file paths in the project without reading their contents."""
    files = get_project_files()
    return "\n".join(files[:200]) or "No files found."
