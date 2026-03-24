# AlphaForge

Native desktop **quant research app** (PySide6) with a local AI copilot (Ollama).

## Core Product Principle
- **Quant Engine computes** indicators, regimes, backtests, and risk metrics.
- **AI Copilot interprets** only structured outputs; it does not compute raw market metrics.

## Current Feature Set
- **Dashboard**: market snapshot + AI snapshot interpretation.
- **Data**: fetch and inspect OHLCV rows.
- **Indicators & Regime**: MA/RSI/volatility + regime labeling + AI insight + chat.
- **Backtest**: moving-average crossover backtest with commission/slippage costs + AI explanation + chat.
- **Portfolio Risk**: weighted portfolio return/volatility/sharpe/drawdown + correlation summary + AI risk analysis + chat.
- **Run Compare**: multi-symbol comparison table, correlation summary, CSV export.
- **Research Report**: markdown report generation, optional benchmark compare symbol, AI executive summary, save to file.
- **Settings**: edit `.env` values and test local Ollama connectivity.

## Architecture (High Level)
- **UI Layer** (`alphaforge/ui`): Qt views and async task runner.
- **Service Layer** (`alphaforge/services`): orchestration between UI and engines.
- **Quant Core** (`alphaforge/core`): indicators, regime logic, backtester.
- **Data Layer** (`alphaforge/data`): SQLite schema + yfinance provider + cache handling.
- **AI Layer** (`alphaforge/ai`): Ollama client, prompts, fallback model orchestration.

## Database
AlphaForge initializes a local SQLite database at startup.

### Declared tables
- `research_sessions`
- `analysis_runs`
- `run_metrics_snapshot`
- `price_cache`

### Active runtime usage
- Current market-data pipeline actively reads/writes `price_cache` for resilience and reuse.

## Quick Start
1. Create and activate a virtual environment:
   - Linux/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows PowerShell:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install and run Ollama locally:
   ```bash
   ollama serve
   ```
4. Pull recommended model(s):
   ```bash
   ollama pull phi3
   ollama pull mistral   # optional fallback model
   ```
5. Launch app:
   ```bash
   python app.py
   ```

## Environment Variables
AlphaForge loads `.env` from the project root.

- `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
- `OLLAMA_PRIMARY_MODEL` (default: `phi3`)
- `OLLAMA_FALLBACK_MODEL` (default: `mistral`)
- `OLLAMA_TIMEOUT_SECONDS` (default: `25`)
- `ALPHAFORGE_DB_PATH` (default: `data/alphaforge.db`)

> Note: `.env.example` currently contains legacy OpenAI/Gemini template keys; runtime configuration is Ollama-based as listed above.

## Testing
Install dev dependencies and run tests:

```bash
pip install -r requirements-dev.txt
pytest
python -m compileall alphaforge app.py
```

## Troubleshooting
- **Ollama unreachable**: ensure `ollama serve` is running and `OLLAMA_BASE_URL` is correct.
- **Primary model missing**: pull model with `ollama pull <model_name>`.
- **Data fetch errors**: retry with a shorter date range; app will use cache fallback when available.

## Additional Documentation
- `PROJECT_FULL_REPORT.md` — deep technical documentation of the current repository.
- `DEMO_SCRIPT.md` — timed live demo script.
- `PRESENTATION_CHECKLIST.md` — operational presenter checklist.
