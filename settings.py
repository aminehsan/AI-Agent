from pathlib import Path
from typing import ClassVar, Literal

from pydantic import (
    AnyHttpUrl,
    DirectoryPath,
    PositiveInt,
    SecretStr,
    field_validator,
    validate_call,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().with_name(".env"),
        env_file_encoding="utf-8",
        env_parse_none_str="None",
        extra="ignore",
    )

    PROJECT_STATE_DIRECTORY_NAME: ClassVar[str] = ".agent"

    model_base_url: AnyHttpUrl | None
    model_api_key: SecretStr
    model_name: str
    model_max_output_tokens: PositiveInt | None
    model_reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"]
    model_verbosity: Literal["low", "medium", "high"]
    model_compaction_threshold: PositiveInt

    agent_name: str
    agent_instructions: str
    session_id: str

    run_max_turns: PositiveInt | None
    session_history_limit: PositiveInt | None

    project_root: DirectoryPath

    @field_validator("project_root")
    @classmethod
    def validate_project_root(cls, path: Path) -> Path:
        if not path.is_absolute():
            raise ValueError("PROJECT_ROOT must be an absolute path.")
        return path.resolve()

    @validate_call(validate_return=True)
    def ensure_project_state_directory(self) -> DirectoryPath:
        state_directory = self.project_root / self.PROJECT_STATE_DIRECTORY_NAME
        state_directory.mkdir(parents=True, exist_ok=True)
        gitignore = state_directory / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n", encoding="utf-8")
        return state_directory

    @property
    def session_database_path(self) -> Path:
        return self.ensure_project_state_directory() / "conversation.db"

    @property
    def excluded_project_directories(self) -> frozenset[Path]:
        directories = (
            self.PROJECT_STATE_DIRECTORY_NAME,
            ".idea",
            ".vscode",
            ".venv",
        )
        return frozenset(self.project_root / directory for directory in directories)


settings = Settings()
