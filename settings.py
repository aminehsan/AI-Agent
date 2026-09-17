from pathlib import Path
from typing import ClassVar
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import (
    AnyHttpUrl,
    DirectoryPath,
    SecretStr,
    field_validator,
    validate_call,
)


class Settings(BaseSettings):
    project_state_directory_name: ClassVar[str] = ".agent"

    model_url: AnyHttpUrl | None
    model_key: SecretStr
    model_name: str
    agent_name: str = "Coding Assistant"
    agent_instructions: str = "You are a programming assistant."
    session_id: str = "default"
    project_root: DirectoryPath

    @property
    def model_base_url(self) -> str | None:
        if self.model_url is None:
            return None
        return str(self.model_url)

    @property
    def model_api_key(self) -> str:
        return self.model_key.get_secret_value()

    @validate_call(validate_return=True)
    def project_state_directory(self) -> DirectoryPath:
        path = self.project_root / self.project_state_directory_name
        path.mkdir(parents=True, exist_ok=True)
        gitignore = path / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n", encoding="utf-8")
        return path

    @property
    def conversation_database_path(self) -> Path:
        return self.project_state_directory() / "conversation.db"

    @property
    def workflow_database_path(self) -> Path:
        return self.project_state_directory() / "workflow.db"

    @field_validator("project_root")
    @classmethod
    def validate_project_root(cls, path: Path) -> Path:
        if not path.is_absolute():
            raise ValueError("PROJECT_ROOT must be an absolute path.")
        return path.resolve()

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().with_name(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
