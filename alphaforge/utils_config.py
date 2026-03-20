from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

@dataclass(frozen=True)
class AppConfig:
    openai_api_key: str
    gemini_api_key: str
    default_ai_provider: str
    openai_model: str
    gemini_model: str
    db_path: Path

def load_config() -> AppConfig:
    load_dotenv()
    repo_root = Path(__file__).resolve().parents[2]
    db_rel = os.getenv("ALPHAFORGE_DB_PATH", "data/alphaforge.db")
    return AppConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY",""),
        gemini_api_key=os.getenv("GEMINI_API_KEY",""),
        default_ai_provider=os.getenv("DEFAULT_AI_PROVIDER","openai"),
        openai_model=os.getenv("OPENAI_MODEL","gpt-4.1-mini"),
        gemini_model=os.getenv("GEMINI_MODEL","gemini-1.5-pro"),
        db_path=(repo_root / db_rel).resolve(),
    )
