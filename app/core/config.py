"""
ArkLog - Application Configuration

Centralized settings using Pydantic Settings. All values can be overridden
via environment variables or the .env file. Import `settings` everywhere.
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

    # ── Application ──────────────────────────────────────────────
    app_name: str = "ArkLog"
    app_version: str = "0.1.0"
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)

    # ── API Server ───────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_prefix: str = "/api/v1"

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: list[str] = Field(default=["*"])

    # ── Security ─────────────────────────────────────────────────
    github_webhook_secret: str = Field(default="")

    # ── Database ─────────────────────────────────────────────────
    database_url: str = Field(default="sqlite+aiosqlite:///./data/arklog.db")

    # ── AI Provider ──────────────────────────────────────────────
    # Compatible with any OpenAI-format API (OpenRouter, OpenAI, etc.)
    # Env vars: AI_API_KEY, AI_BASE_URL, AI_MODEL, AI_MAX_TOKENS, AI_TEMPERATURE
    ai_api_key: str = Field(default="")
    ai_base_url: str = Field(default="https://openrouter.ai/api/v1")
    ai_model: str = Field(default="google/gemini-2.5-flash")
    ai_max_tokens: int = Field(default=2000)
    ai_temperature: float = Field(default=0.3)

    # ── ClickUp ──────────────────────────────────────────────────
    clickup_api_token: str = Field(default="")
    clickup_team_id: str = Field(default="")
    clickup_base_url: str = "https://api.clickup.com/api/v2"

    # ── Projects ─────────────────────────────────────────────────
    projects_config_path: str = Field(default="projects.yaml")

    # ── Scheduler ────────────────────────────────────────────────
    # Set SCHEDULER_ENABLED=false on replica containers to prevent duplicate reports
    scheduler_enabled: bool = Field(default=True)

    # ── Webhook ──────────────────────────────────────────────────
    max_commits_per_webhook: int = Field(default=50)

    # ── Logging ──────────────────────────────────────────────────
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")  # json | text

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


settings = Settings()
