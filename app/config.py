from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime settings. Secrets come from the environment / .env only."""

    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    judge_model: str = "claude-sonnet-5-5"
    source_ttl_days: int = 30
    chat_rate_per_min: int = 10
    chat_daily_cap: int = 400
    read_rate_per_min: int = 240  # library and sensor lookups, per client
    trusted_proxy_hops: int = 1  # proxies in front of the app whose X-Forwarded-For entry can be trusted

    narrations_path: Path = ROOT / "data" / "narrations.json"
    islands_dir: Path = ROOT / "data" / "islands"
    snapshots_dir: Path = ROOT / "data" / "snapshots"
    cache_dir: Path = ROOT / "data" / "cache"
    web_dir: Path = ROOT / "web"


# Search box (± degrees around each pin) used for GBIF "records near the island" counts.
# Chosen so each box covers the island group the facts describe, and stated verbatim in the evidence text.
GBIF_BOX_DEG: dict[str, float] = {
    "cocos-keeling": 1.0,
    "galapagos": 3.0,
    "socotra": 1.5,
    "tristan-da-cunha": 4.0,
    "pitcairn": 2.0,
    "clipperton": 1.0,
    "bouvet": 1.0,
}


def get_settings() -> Settings:
    return Settings()
