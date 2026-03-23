from pathlib import Path

from alphaforge.services.view_helpers import (
    has_required_settings_fields,
    resolve_env_path,
    write_env_file,
)
from alphaforge.utils_config import get_env_path


def test_has_required_fields_requires_core_values():
    valid = {
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_PRIMARY_MODEL": "phi3",
        "OLLAMA_FALLBACK_MODEL": "mistral",
        "ALPHAFORGE_DB_PATH": "data/alphaforge.db",
    }

    assert has_required_settings_fields(valid)

    missing_db = {**valid, "ALPHAFORGE_DB_PATH": ""}
    assert not has_required_settings_fields(missing_db)


def test_resolve_env_path_uses_base_dir_when_provided(tmp_path: Path):
    resolved = resolve_env_path(tmp_path)

    assert resolved == tmp_path / ".env"


def test_resolve_env_path_resolves_relative_to_project_root():
    resolved = resolve_env_path(Path(".env"))

    assert resolved == get_env_path().resolve()


def test_write_env_file_writes_expected_content(tmp_path: Path):
    env_path = tmp_path / ".env"
    values = {
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_PRIMARY_MODEL": "phi3",
        "OLLAMA_FALLBACK_MODEL": "mistral",
        "OLLAMA_TIMEOUT_SECONDS": "25",
        "ALPHAFORGE_DB_PATH": "data/alphaforge.db",
    }

    write_env_file(env_path, values)

    assert env_path.read_text(encoding="utf-8") == (
        "OLLAMA_BASE_URL=http://localhost:11434\n"
        "OLLAMA_PRIMARY_MODEL=phi3\n"
        "OLLAMA_FALLBACK_MODEL=mistral\n"
        "OLLAMA_TIMEOUT_SECONDS=25\n"
        "ALPHAFORGE_DB_PATH=data/alphaforge.db\n"
    )
