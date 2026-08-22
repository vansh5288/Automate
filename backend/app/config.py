"""Central configuration loaded from environment variables.

Nothing here should ever contain a real secret - values come from .env
(loaded via pydantic-settings) which is gitignored.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./procureflow.db"

    notion_token: str = ""
    notion_requests_database_id: str = ""
    notion_approvals_database_id: str = ""
    notion_run_log_database_id: str = ""

    ai_provider: str = "mock"  # openai | anthropic | mock
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"

    auto_approval_limit: float = 10000
    min_ai_confidence: float = 0.80

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    procurement_email: str = "procurement@example.com"
    email_from: str = "procureflow@example.com"

    webhook_secret: str = "change-me"

    notion_poll_interval_seconds: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
