# Presentation Checklist (Live Demo)

## 1) Startup (5 minutes before audience joins)
1. Open terminal in repo root and activate environment:
   - `python -m venv .venv`
   - `source .venv/bin/activate` (macOS/Linux) or `./.venv/Scripts/Activate.ps1` (Windows PowerShell)
   - `pip install -r requirements.txt`
2. Start Ollama in a separate terminal: `ollama serve`
3. Verify model is present (recommended default): `ollama pull phi3`
4. Launch app: `python app.py`
5. In **Settings** tab, click **Test Connection** and confirm success message.

## 2) Exact click path by tab (left nav order)
Use this sequence to avoid backtracking:

### Dashboard
- Click path: `Dashboard` → keep `AAPL` + date range → **Refresh Snapshot** → **AI Snapshot Insight**.
- Say:
  - “The quant engine computes all metrics first; AI only interprets structured output.”
  - “We get a quick market state read (return, RSI, volatility, regime) plus AI commentary.”

### Data
- Click path: `Data` → keep `AAPL` + date range → **Fetch Data**.
- Say:
  - “Raw OHLCV data is visible so we can validate inputs before any strategy logic.”
  - “This confirms data quality and source before analysis.”

### Indicators & Regime
- Click path: `Indicators & Regime` → **Compute** → **AI Insight** (optional: ask follow-up in chat panel).
- Say:
  - “We compute MA fast/slow, RSI, and regime labels directly in-app.”
  - “AI explains the computed state; it does not recalculate indicators.”

### Backtest
- Click path: `Backtest` → leave commission/slippage defaults → **Run MA Backtest** → **Explain this strategy result**.
- Say:
  - “This is a cost-aware MA crossover backtest with explicit bps assumptions.”
  - “We focus on return, vol, Sharpe, and drawdown before interpretation.”

### Portfolio Risk
- Click path: `Portfolio Risk` → keep `AAPL:0.6,MSFT:0.4` → **Compute Risk** → **Analyze portfolio risk**.
- Say:
  - “Portfolio risk uses weighted returns and correlation, not single-asset metrics.”
  - “AI summarizes concentration and diversification tradeoffs from computed stats.”

### Run Compare
- Click path: `Run Compare` → keep `AAPL,MSFT,NVDA` → **Compare** → check table ranking → enable **Show correlation summary**.
- Say:
  - “We benchmark multiple symbols in one run with common metrics.”
  - “Correlation summary adds a diversification lens to performance ranking.”

### Research Report
- Click path: `Research Report` → **Generate Report** → **AI Executive Summary** → **Save Report** (optional).
- Say:
  - “This tab packages analysis + backtest into a reusable markdown artifact.”
  - “Executive summary is layered on top of deterministic computed numbers.”

### Settings (close)
- Click path: `Settings` → review URL/models/timeout/path → **Test Connection** (or **Save .env** if needed).
- Say:
  - “Config is local and explicit; changing providers/models is controlled here.”
  - “If AI is unavailable, the quant workflow still runs end-to-end.”

## 3) Fallback plan (Ollama or network failure)

### If Ollama fails
- Symptom: any AI button ends with `AI unavailable` or connection test fails.
- Action:
  1. Continue demo using quant tabs only (Dashboard/Data/Indicators/Backtest/Portfolio/Run Compare).
  2. Narrate: “AI is optional; all core analytics are deterministic and local.”
  3. If time allows, go to **Settings** → **Test Connection** to show failure handling.

### If market-data/network fails
- Symptom: fetch/compare/report shows network/provider error.
- Action:
  1. Retry once with a smaller date range (e.g., last 3 months).
  2. Switch to already-loaded tab outputs and walk through interpretation.
  3. Narrate: “Error handling is explicit in UI; failures are surfaced and non-destructive.”

## 4) Presenter ready check (30 seconds)
- App open and left-nav tabs visible.
- At least one successful run completed in **Data** and **Backtest**.
- AI path validated once (or fallback statement prepared).
