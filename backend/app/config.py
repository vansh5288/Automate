"""Central configuration loaded from environment variables.

Nothing here should ever contain a real secret - values come from .env
(loaded via pydantic-settings) which is gitignored.
"""
from functools import lru_cache
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./procureflow.db"

    notion_token: str = ""
    notion_parent_page_id: str = ""
    notion_api_version: str = "2022-06-28"
    notion_requests_database_id: str = Field(
        default="", validation_alias=AliasChoices("NOTION_REQUESTS_DATABASE_ID", "NOTION_PURCHASE_REQUESTS_DB_ID")
    )
    notion_approvals_database_id: str = Field(
        default="", validation_alias=AliasChoices("NOTION_APPROVALS_DATABASE_ID", "NOTION_APPROVAL_QUEUE_DB_ID")
    )
    notion_run_log_database_id: str = Field(
        default="", validation_alias=AliasChoices("NOTION_RUN_LOG_DATABASE_ID", "NOTION_RUN_LOG_DB_ID")
    )

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
    demo_mode: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
