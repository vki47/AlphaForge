# AlphaForge Web Terminal UI

The browser interface is now AlphaForge’s only UI. It contains all eight former
desktop workspaces: Dashboard, Market Data, Indicators & Regime, Backtest,
Portfolio Risk, Run Compare, Research Report, and Settings. The global command
palette and collapsible Copilot remain available from every workspace.

## Run

From the repository root:

```bash
python app.py
```

Open `http://127.0.0.1:8080`. Use `--host` and `--port` to change the bind
address. The current browser interactions demonstrate the complete workflow and
form the presentation boundary for connecting the existing Python services to
HTTP endpoints.

## Product rule

The quant engine computes values. The AI Copilot only interprets structured
outputs. The UI repeats that boundary wherever AI actions are available.
