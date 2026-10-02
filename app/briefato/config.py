"""Briefato — application configuration (env driven, prefix ``BRIEFATO_``)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BRIEFATO_", env_file=".env", extra="ignore")

    # --- app ---
    app_name: str = "Briefato"
    env: str = "dev"  # dev | staging | prod
    base_url: str = "http://localhost:8080"
    secret_key: str = "dev-secret-change-me"
    data_dir: Path = Path("/tmp/briefato-data")
    db_url: str = ""
    ui_lang: str = "de"
    admin_email: str = ""
    session_ttl_hours: int = 336  # 14 days
    quota_default_letters: int = 10
    login_max_attempts: int = 10
    login_window_minutes: int = 15

    # --- model layer ---
    llm_base_url: str = "https://api.mistral.ai/v1"
    llm_api_key: str = ""
    llm_model: str = "mistral-large-latest"
    llm_timeout_s: int = 180
    llm_mock: bool = True
    llm_cost_in_per_1k: float = 0.0
    llm_cost_out_per_1k: float = 0.0

    # --- crypto ---
    field_key: str = ""  # Fernet key; dev falls back to a derived key (see security.py)

    # --- billing ---
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_praxis: str = ""
    stripe_price_klinik: str = ""

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @property
    def sqlalchemy_url(self) -> str:
        return self.db_url or f"sqlite:///{self.data_dir / 'briefato.db'}"

    @property
    def letters_dir(self) -> Path:
        return self.data_dir / "letters"

    @property
    def landing_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "landing"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.letters_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings


PLAN_CATALOG: dict[str, dict] = {
    "free": {"label": "Test", "price_eur": 0.0, "letters": 10},
    "starter": {"label": "Starter", "price_eur": 19.0, "letters": 40},
    "praxis": {"label": "Praxis", "price_eur": 39.0, "letters": 120},
    "klinik": {"label": "Klinik", "price_eur": 89.0, "letters": 400},
}
