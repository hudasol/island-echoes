from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime settings. Secrets come from the environment / .env only."""

    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    anthropic_api_key: str | None = None
    llm_provider: str | None = None  # off | extractive | ollama | llamacpp | huggingface | openai-compat | anthropic
    llm_model: str | None = None  # model name for the chosen provider (each has a sensible default)
    ollama_url: str = "http://localhost:11434"
    hf_token: str | None = None  # free Hugging Face token, only for LLM_PROVIDER=huggingface
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    llamacpp_model_path: Path | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    judge_model: str = "claude-sonnet-5-5"
    source_ttl_days: int = 30
    chat_rate_per_min: int = 10
    chat_daily_cap: int = 400
    read_rate_per_min: int = 240  # library and sensor lookups, per client
    trusted_proxy_hops: int = 1  # proxies in front of the app whose X-Forwarded-For entry can be trusted

    retrieval_mode: str = "bm25"  # bm25 | dense | hybrid (dense needs requirements-ml.txt)
    embeddings_path: Path = ROOT / "data" / "embeddings" / "bge-small-en-v1.5.npz"
    retrieval_k: int = 12  # facts shown to the model (fewer = faster on small local models)
    dense_min_sim: float = 0.55  # cosine floor for the dense side of the answerability gate

    telemetry: bool = True
    log_questions: bool = False  # store question text (off by default: only a hash and length are kept)
    telemetry_path: Path = ROOT / "data" / "cache" / "telemetry.db"

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
