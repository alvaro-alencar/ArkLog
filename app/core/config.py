"""
ArkLog - Application Configuration.

All secrets remain server-side. The web client never receives the OpenRouter key.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "ArkLog"
    app_version: str = "0.2.0"
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)

    # API server
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default=["http://localhost:5173"])

    # Shared Ark account identity provider
    ark_auth_me_url: str = Field(
        default="https://www.arksystem.net/api/saas?action=me"
    )
    ark_auth_timeout_seconds: float = Field(default=8.0)
    arklog_admin_emails: str = Field(default="")
    arklog_auto_trial: bool = Field(default=False)
    arklog_trial_report_limit: int = Field(default=1)
    arklog_active_report_limit: int = Field(default=50)
    arklog_trial_max_window_hours: int = Field(default=168)
    arklog_trial_max_projects: int = Field(default=1)

    # GitHub
    github_webhook_secret: str = Field(default="")
    github_token: str = Field(default="")
    github_client_id: str = Field(default="")
    github_client_secret: str = Field(default="")
    github_redirect_uri: str = Field(default="http://localhost:5173/auth/callback")

    # Legacy JWT settings kept only for backward-compatible configuration parsing.
    # ArkLog no longer accepts these tokens for application access.
    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./data/arklog.db")

    # AI provider
    ai_api_key: str = Field(default="")
    ai_base_url: str = Field(default="https://openrouter.ai/api/v1")
    ai_model: str = Field(default="google/gemini-2.5-flash")
    ai_trial_model: str = Field(default="google/gemini-2.5-flash")
    ai_max_tokens: int = Field(default=2000)
    ai_max_tokens_backfill: int = Field(default=8000)
    ai_trial_max_tokens: int = Field(default=1200)
    ai_temperature: float = Field(default=0.3)
    ai_max_prompt_chars: int = Field(default=120_000)
    ai_trial_max_prompt_chars: int = Field(default=30_000)

    # ClickUp
    clickup_api_token: str = Field(default="")
    clickup_team_id: str = Field(default="")
    clickup_base_url: str = "https://api.clickup.com/api/v2"

    projects_config_path: str = Field(default="projects.yaml")

    # Scheduler. Keep disabled on serverless replicas.
    scheduler_enabled: bool = Field(default=False)
    scheduler_timezone: str = Field(default="America/Sao_Paulo")

    max_commits_per_webhook: int = Field(default=50)
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def admin_email_set(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.arklog_admin_emails.split(",")
            if item.strip()
        }


settings = Settings()
