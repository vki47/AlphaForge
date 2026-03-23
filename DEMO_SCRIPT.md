# 6-Minute Demo Script (Timed Flow)

## 0:00–0:30 — Open + framing
- “AlphaForge is a desktop quant research app. Core rule: quant engine computes, AI interprets.”
- Show left navigation and top toolbar statement.

## 0:30–1:10 — Data sanity check
- Go to **Data**.
- Click **Fetch Data** (AAPL, default dates).
- Talk track:
  - “I start from raw market data before indicators or strategy conclusions.”
  - “This gives us transparent, auditable inputs.”

## 1:10–2:00 — Snapshot + regime context
- Go to **Dashboard**.
- Click **Refresh Snapshot**, then **AI Snapshot Insight**.
- Talk track:
  - “Snapshot condenses return, RSI, volatility, and regime in one pass.”
  - “AI commentary is generated from these computed fields.”

## 2:00–2:50 — Indicators deep dive
- Go to **Indicators & Regime**.
- Click **Compute**, then **AI Insight**.
- Optional: ask one short follow-up in chat panel.
- Talk track:
  - “This table shows indicator history and the current trend regime.”
  - “Useful for turning raw price history into decision context.”

## 2:50–3:50 — Strategy test
- Go to **Backtest**.
- Keep default commission/slippage.
- Click **Run MA Backtest**, then **Explain this strategy result**.
- Talk track:
  - “We evaluate return, volatility, Sharpe, and max drawdown with costs included.”
  - “AI summarizes strengths/weaknesses of the measured outcome.”

## 3:50–4:40 — Portfolio view
- Go to **Portfolio Risk**.
- Click **Compute Risk** and **Analyze portfolio risk**.
- Talk track:
  - “Now we move from single asset to weighted portfolio behavior.”
  - “Correlation and drawdown help explain diversification quality.”

## 4:40–5:20 — Multi-symbol comparison
- Go to **Run Compare**.
- Click **Compare**, then enable **Show correlation summary**.
- Talk track:
  - “This ranks candidates side-by-side on consistent metrics.”
  - “Correlation summary keeps us honest about concentration risk.”

## 5:20–6:00 — Report + close
- Go to **Research Report**.
- Click **Generate Report**, then **AI Executive Summary**.
- Optional: **Save Report**.
- Close with **Settings** briefly (Test Connection).
- Talk track:
  - “Final output is a shareable markdown report with both quant and narrative layers.”
  - “If AI is down, quant workflow still runs, and reporting remains usable.”

## Backup lines (use only if something fails)
- **Ollama down:** “AI is optional in this architecture; all numbers still compute locally.”
- **Network/data issue:** “Provider errors are surfaced clearly; we can continue from previously computed outputs.”
