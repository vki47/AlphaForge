# AlphaForge

Native desktop (PySide6) quant research app with a local AI copilot.

## Architecture
- **Quant Engine** computes all indicators, backtests, and risk numbers.
- **AI Copilot (Ollama)** only interprets structured outputs; it never computes raw metrics.

## Quick start
1. `python -m venv .venv`
2. `source .venv/bin/activate` (Linux/macOS) or `.\.venv\Scripts\Activate.ps1` (Windows)
3. `pip install -r requirements.txt`
4. Install and run Ollama locally: `ollama serve`
5. Pull lightweight model(s): `ollama pull phi3` and optional `ollama pull mistral`
6. `python app.py`

## Optional environment variables
- `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
- `OLLAMA_PRIMARY_MODEL` (default: `phi3`)
- `OLLAMA_FALLBACK_MODEL` (default: `mistral`)
- `OLLAMA_TIMEOUT_SECONDS` (default: `25`)
- `ALPHAFORGE_DB_PATH` (default: `data/alphaforge.db`)


## Testing
1. Install dev dependencies: `pip install -r requirements-dev.txt`
2. Run unit tests: `pytest`
3. Run syntax check: `python -m compileall alphaforge app.py`
