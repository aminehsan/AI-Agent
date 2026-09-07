from pathlib import Path
from pydantic import DirectoryPath, SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_url: str | None = None
    model_key: SecretStr
    model_name: str
    agent_name: str
    agent_instructions: str
    session_id: str = "default"
    database_name: str = "conversation.db"
    project_root: DirectoryPath
    project_state_directory_name: str = ".agent"

    @computed_field
    @property
    def project_state_directory(self) -> DirectoryPath:
        return self.project_root / self.project_state_directory_name

    @field_validator("project_root")
    @classmethod
    def validate_project_root(cls, path: Path) -> Path:
        if not path.is_absolute():
            raise ValueError("PROJECT_ROOT must be an absolute path.")
        return path.resolve()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
