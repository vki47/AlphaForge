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


def load_config() -> AppConfig:
    load_dotenv()
    repo_root = Path(__file__).resolve().parents[2]
    db_rel = os.getenv("ALPHAFORGE_DB_PATH", "data/alphaforge.db")
    return AppConfig(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_primary_model=os.getenv("OLLAMA_PRIMARY_MODEL", "phi3"),
        ollama_fallback_model=os.getenv("OLLAMA_FALLBACK_MODEL", "mistral"),
        ollama_timeout_seconds=int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "25")),
        db_path=(repo_root / db_rel).resolve(),
    )
