from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    ollama_base_url: str
    ollama_primary_model: str
    ollama_fallback_model: str
    ollama_timeout_seconds: int
    db_path: Path


def get_config_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_env_path() -> Path:
    return get_config_root() / ".env"


def load_config() -> AppConfig:
    load_dotenv(dotenv_path=get_env_path(), override=False)
    config_root = get_config_root()
    db_raw = os.getenv("ALPHAFORGE_DB_PATH", "data/alphaforge.db").strip()
    db_candidate = Path(db_raw).expanduser()
    db_path = db_candidate if db_candidate.is_absolute() else (config_root / db_candidate)
    return AppConfig(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_primary_model=os.getenv("OLLAMA_PRIMARY_MODEL", "phi3"),
        ollama_fallback_model=os.getenv("OLLAMA_FALLBACK_MODEL", "mistral"),
        ollama_timeout_seconds=int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "25")),
        db_path=db_path.resolve(),
    )
