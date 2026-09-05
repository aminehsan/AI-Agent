from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_url: str | None = None
    model_key: SecretStr
    model_name: str
    agent_name: str
    agent_instructions: str
    session_id: str
    session_db_path: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
