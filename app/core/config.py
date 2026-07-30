"""ArkLog application configuration.

Platform secrets stay on the server. Personal provider connections are created by
provider installation/OAuth flows and stored encrypted per Ark user and organization.
"""

import os

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
    app_version: str = "0.4.0"
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)
    public_app_url: str = Field(default="http://localhost:5173")

    # API server
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_prefix: str = "/api/v1"
    public_api_prefix: str = "/api/arklog/v1"
    cors_origins: list[str] = Field(default=["http://localhost:5173"])

    # Shared Ark account identity provider
    ark_auth_me_url: str = Field(
        default="https://www.arksystem.net/api/saas?action=me"
    )
    ark_auth_timeout_seconds: float = Field(default=8.0, gt=0, le=30)
    arklog_admin_emails: str = Field(default="")
    arklog_auto_trial: bool = Field(default=False)
    arklog_trial_report_limit: int = Field(default=1, ge=0, le=1)
    arklog_active_report_limit: int = Field(default=50, ge=-1)
    arklog_trial_max_window_hours: int = Field(default=168, ge=1, le=168)
    arklog_trial_max_projects: int = Field(default=1, ge=1, le=1)

    # Credential vault and signed provider state. These belong to ArkLog, not to a user.
    connections_encryption_key: str = Field(default="")
    oauth_state_secret: str = Field(default="")
    oauth_state_ttl_seconds: int = Field(default=600, ge=120, le=1800)

    # GitHub App owned by ArkLog. Users install it only on repositories they choose.
    # Installation access tokens are generated on demand and expire automatically.
    github_app_id: str = Field(default="")
    github_app_slug: str = Field(default="")
    github_app_private_key: str = Field(default="")
    github_client_id: str = Field(default="")
    github_client_secret: str = Field(default="")
    github_setup_uri: str = Field(
        default="http://localhost:8000/api/v1/connections/github/setup"
    )
    github_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/connections/github/callback"
    )
    github_api_version: str = Field(default="2022-11-28")

    # Slack OAuth application. The resulting bot token belongs to the connected workspace.
    slack_client_id: str = Field(default="")
    slack_client_secret: str = Field(default="")
    slack_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/connections/slack/callback"
    )

    # Legacy webhook parsing remains available, but it has no owner access token.
    github_webhook_secret: str = Field(default="")

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./data/arklog.db")

    # AI provider. This is the metered platform service sold by ArkLog.
    ai_api_key: str = Field(default="")
    ai_base_url: str = Field(default="https://openrouter.ai/api/v1")
    ai_model: str = Field(default="google/gemini-2.5-flash")
    ai_trial_model: str = Field(default="google/gemini-2.5-flash")
    ai_max_tokens: int = Field(default=2000, ge=1, le=16000)
    ai_max_tokens_backfill: int = Field(default=8000, ge=1, le=32000)
    ai_trial_max_tokens: int = Field(default=1200, ge=1, le=1200)
    ai_temperature: float = Field(default=0.3, ge=0, le=1)
    ai_max_prompt_chars: int = Field(default=120_000, ge=1, le=500_000)
    ai_trial_max_prompt_chars: int = Field(default=30_000, ge=1, le=30_000)

    # Provider base URLs contain no account credentials.
    github_api_base_url: str = "https://api.github.com"
    slack_api_base_url: str = "https://slack.com/api"

    # Inert legacy fields retained only so old modules/tests can import safely.
    # They are not documented, wired at startup, or used by the new flow engine.
    clickup_api_token: str = Field(default="")
    clickup_team_id: str = Field(default="")
    clickup_base_url: str = "https://api.clickup.com/api/v2"

    projects_config_path: str = Field(default="projects.yaml")

    # Scheduling will be reintroduced through a single external scheduler/queue.
    scheduler_enabled: bool = Field(default=False)
    scheduler_timezone: str = Field(default="America/Sao_Paulo")

    max_commits_per_webhook: int = Field(default=50, ge=1, le=100)
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_cloud(self) -> bool:
        """Return true on Vercel even when APP_ENV was accidentally omitted."""
        return bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))

    @property
    def requires_secure_configuration(self) -> bool:
        return self.is_production or self.is_cloud

    @property
    def is_development(self) -> bool:
        return self.app_env == "development" and not self.is_cloud

    @property
    def github_app_configured(self) -> bool:
        return all(
            item.strip()
            for item in (
                self.github_app_id,
                self.github_app_slug,
                self.github_app_private_key,
                self.github_client_id,
                self.github_client_secret,
                self.github_setup_uri,
                self.github_redirect_uri,
            )
        )

    @property
    def slack_oauth_configured(self) -> bool:
        return all(
            item.strip()
            for item in (
                self.slack_client_id,
                self.slack_client_secret,
                self.slack_redirect_uri,
            )
        )

    @property
    def admin_email_set(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.arklog_admin_emails.split(",")
            if item.strip()
        }


settings = Settings()
