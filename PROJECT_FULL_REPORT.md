# AlphaForge Full Project Report

## 1) Project Identity and Purpose
- **Project name:** AlphaForge.
- **Application type:** Native desktop quant research app with local AI copilot.
- **Primary UX statement:** Quant engine computes values; AI interprets structured outputs.
- **Main entrypoint:** `app.py` imports and runs `run_app()`.

## 2) Runtime Stack and Dependencies
- **Language:** Python.
- **UI framework:** PySide6 (Qt desktop UI).
- **Data + numerical stack:** pandas, numpy.
- **Data source:** yfinance.
- **Config/env loading:** python-dotenv.
- **Testing:** pytest.

Dependencies declared in:
- `requirements.txt`
- `requirements-dev.txt`
- `pytest.ini`

## 3) Repository Top-Level Contents
- App/runtime files: `app.py`, `README.md`, `requirements*.txt`, `pytest.ini`.
- Docs/presentation: `DEMO_SCRIPT.md`, `PRESENTATION_CHECKLIST.md`.
- Setup helper: `bootstrap.ps1`.
- Source package: `alphaforge/`.
- Tests: `tests/`.
- Environment scaffolding: `.env.example`, `.gitignore`, `.gitkeep`.

## 4) Configuration and Environment Variables
`alphaforge/utils_config.py` defines:
- `AppConfig` dataclass fields:
  - `ollama_base_url`
  - `ollama_primary_model`
  - `ollama_fallback_model`
  - `ollama_timeout_seconds`
  - `db_path`
- `load_config()` behavior:
  - Loads `.env` from project root path.
  - Reads defaults if variables absent.
  - Resolves DB path absolute from project root when relative.

Documented runtime vars (`README.md`):
- `OLLAMA_BASE_URL` default `http://localhost:11434`
- `OLLAMA_PRIMARY_MODEL` default `phi3`
- `OLLAMA_FALLBACK_MODEL` default `mistral`
- `OLLAMA_TIMEOUT_SECONDS` default `25`
- `ALPHAFORGE_DB_PATH` default `data/alphaforge.db`

Note: `.env.example` still contains legacy OpenAI/Gemini variables from bootstrap template and does not match current Ollama-based runtime.

## 5) Logging and Bootstrap Lifecycle
- Logging: `alphaforge/utils_logger.py` sets global INFO logging format.
- Bootstrap pipeline: `alphaforge/services/bootstrap.py`
  1. setup logging
  2. load config
  3. initialize SQLite DB schema
  4. return config

## 6) Database Layer
### 6.1 Engine
- SQLite, via `sqlite3` stdlib.
- DB initialized by `init_db()` in `alphaforge/data/db.py`.

### 6.2 Schema (exact table inventory)
`SCHEMA_SQL` creates:
1. `research_sessions`
   - PK: `session_id`
   - metadata fields + status
2. `analysis_runs`
   - PK: `run_id`
   - FK: `session_id -> research_sessions(session_id)` with cascade delete
   - stores run metadata, strategy/cost JSON blobs, dates, status
3. `run_metrics_snapshot`
   - PK: `run_id`
   - FK: `run_id -> analysis_runs(run_id)` with cascade delete
   - stores key return/risk metrics and JSON regime/risk flags
4. `price_cache`
   - PK composite: `(symbol, interval, date)`
   - stores OHLCV cache rows

### 6.3 Current usage reality
- Active runtime data workflow reads/writes **only `price_cache`** via `DataService`.
- The research/run tables are provisioned but not currently persisted to by services/views.

## 7) Market Data Provider and Resilience
### 7.1 Provider (`alphaforge/data/providers/yfinance_provider.py`)
- `YFinanceProvider.fetch_ohlcv(symbol, start, end, interval='1d')`
- Normalizes symbol to uppercase.
- Calls `yf.Ticker(symbol).history(...)` with `auto_adjust=False`.
- Retries transient failures (`max_retries`, linear backoff via delay * attempt).
- Error classification:
  - `TransientDataProviderError`
  - `PermanentDataProviderError`
- Frame normalization:
  - index reset to `Date`
  - strips timezone
  - outputs canonical columns `[Date, Open, High, Low, Close, Volume]`

### 7.2 Data service (`alphaforge/services/data_service.py`)
- `DataService.fetch()` policy:
  - Attempts provider fetch.
  - On provider failures, falls back to cache when available.
  - Raises user-facing `DataServiceError` messages when no usable cache.
  - If provider returns empty frame, also falls back to cache or raises.
- Caching details:
  - Upsert into `price_cache` with `ON CONFLICT(symbol,interval,date) DO UPDATE`.
  - Reads cache by inclusive start / exclusive end date filter.
  - Converts numeric columns with coercion.

## 8) Quant Core Computation
### 8.1 Indicators (`alphaforge/core/indicators.py`)
Computed columns:
- `return`: close-to-close pct change
- `ma_fast`: 20-day rolling mean
- `ma_slow`: 50-day rolling mean
- `rsi`: 14-window RSI-style calc from avg gains/losses
- `volatility`: rolling std(returns, 20) annualized by sqrt(252)

### 8.2 Regime labeling (`alphaforge/core/regimes.py`)
- Threshold: volatility quantile (default 0.8).
- Labels:
  - `high_vol_uptrend`
  - `high_vol_downtrend`
  - `uptrend`
  - `downtrend`
  - `range`

### 8.3 Backtesting (`alphaforge/core/backtester.py`)
- Strategy: long/flat MA crossover (`ma_fast > ma_slow`).
- Position is lagged one bar (`signal.shift(1)`).
- Costs included:
  - commission bps
  - slippage bps
  - turnover-based cost deduction
- Outputs:
  - total return %
  - annualized return %
  - annualized vol %
  - Sharpe
  - max drawdown %
- Result container: `BacktestResult` dataclass.

## 9) Service Layer Composition
- `AnalysisService`: data fetch -> indicators -> regime classification.
- `BacktestService`: analysis output -> MA backtest engine.
- `demo_defaults.py`: centralized defaults used by multiple views.
- `view_helpers.py`: shared parsing/validation, reporting markdown builder, metrics helpers.

## 10) AI Layer
### 10.1 Client transport (`alphaforge/ai/ollama_client.py`)
- HTTP API against local Ollama `/api/generate`.
- Non-streaming payload.
- Robust error mapping:
  - HTTP errors include status + truncated detail
  - timeout-specific guidance
  - connection-refused guidance
  - invalid JSON / empty response checks

### 10.2 AI service orchestration (`alphaforge/ai/ai_service.py`)
- Tasks:
  - market insight
  - strategy explanation
  - portfolio risk analysis
  - Q&A chat
- Uses model fallback sequence: primary then fallback.
- If both fail, rethrows user-friendly Ollama error.

### 10.3 Prompt policy (`alphaforge/ai/prompts.py`)
- Explicit role text and strict rules:
  - only interpret supplied structured values
  - do not invent market numbers
  - mention missing values explicitly
- Task-specific instructions for each prompt type.

## 11) UI Architecture
### 11.1 Main shell
`alphaforge/ui/main_window.py` builds:
- Top toolbar statement reinforcing quant-vs-AI boundary.
- Left nav + stacked pages.
- Page list:
  1. Dashboard
  2. Data
  3. Indicators & Regime
  4. Backtest
  5. Portfolio Risk
  6. Run Compare
  7. Research Report
  8. Settings

### 11.2 Async background runner
`alphaforge/ui/ai_worker.py`:
- Generic QRunnable wrapper for async tasks.
- Emits `finished` or `failed` signals.
- Error path extracts root cause chain where available.

### 11.3 View-by-view behavior
- **DashboardView**
  - Snapshot metrics from analysis service.
  - AI snapshot interpretation.
- **DataView**
  - Fetches OHLCV and renders table.
  - Uses friendly error classifier tokens.
- **IndicatorsRegimeView**
  - Shows indicator/regime table (tail 120 rows).
  - AI insight + embedded chat panel.
- **BacktestView**
  - Runs MA backtest with commission/slippage controls.
  - AI explanation + embedded chat panel.
- **PortfolioView**
  - Parses weighted allocations.
  - Computes portfolio ann return/vol/sharpe/drawdown and correlation summary.
  - AI portfolio risk interpretation + chat panel.
- **RunCompareView**
  - Multi-symbol metric comparison table.
  - Optional correlation summary panel.
  - CSV export includes rows, skipped symbols, correlation summary.
- **ResearchReportView**
  - Generates markdown report from analysis + backtest (+ optional compare symbol snapshot).
  - AI executive summary can be merged into report.
  - Save report to `.md`.
- **SettingsView**
  - Edits core env settings.
  - Validates required fields and Ollama base URL format.
  - Writes `.env` in project root.
  - Tests Ollama connection via `/api/version`, `/api/tags`, fallback generation ping.

## 12) Shared View Helpers (`alphaforge/services/view_helpers.py`)
Includes:
- Symbol/date validators and normalizers.
- Error-to-friendly-message formatter by token matching.
- Allocation parser with strict validation.
- Correlation summary helper.
- Run-compare metrics helper.
- Research report markdown generator.
- Settings helper functions for required fields, env path resolution, `.env` writing.

## 13) Tests and Coverage Focus
`tests/` suite validates:
- Data service resilience + cache fallback behavior.
- YFinance provider retry/classification behavior.
- Ollama client and AI fallback handling.
- Portfolio helper parsers/correlation summary.
- Run compare metric formulas.
- Research report markdown section inclusion logic.
- Settings helper validation/path/write behavior.

## 14) Documentation and Operational Material
- `README.md`: architecture statement, quickstart, env vars, testing commands.
- `DEMO_SCRIPT.md`: timed six-minute demo script and fallback lines.
- `PRESENTATION_CHECKLIST.md`: startup checklist, click path per tab, failure fallbacks.

## 15) Packaging / Module Export Notes
- Most `__init__.py` files are empty package markers.
- `alphaforge/ai/__init__.py` re-exports `AIService`, `OllamaClient`, `OllamaClientError`.

## 16) Legacy/Template Artifacts to Be Aware Of
- `bootstrap.ps1` and `.env.example` include old OpenAI/Gemini scaffolding from initial template.
- Current runtime codepath uses Ollama-local configuration and does not consume those OpenAI/Gemini keys.

## 17) End-to-End Execution Flow (Current)
1. `app.py` calls `run_app()`.
2. Bootstrap initializes logging, config, and DB schema.
3. Main window wires services and views.
4. UI view action triggers service methods.
5. Data path: yfinance fetch -> normalization -> cache upsert -> analysis/backtest.
6. AI path: view context dict -> prompt builder -> Ollama client (primary/fallback model) -> UI text output.

## 18) Security / Risk Posture (Current Code Behavior)
- No remote AI calls by default; expects local Ollama endpoint.
- Data provider is internet-based (yfinance).
- `.env` writing is plain text and local filesystem based.
- No auth/encryption abstractions in repo for provider/AI endpoints.
- Research report and AI outputs include educational-not-advice language in generated markdown.
