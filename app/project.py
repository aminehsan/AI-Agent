from pathlib import Path
from .settings import settings


def get_project_state_directory() -> Path:
    settings.project_state_directory.mkdir(parents=True, exist_ok=True)
    gitignore = settings.project_state_directory / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n", encoding="utf-8")
    return settings.project_state_directory


def get_session_database_path() -> Path:
    return get_project_state_directory() / settings.database_name
