from __future__ import annotations
import sqlite3
from pathlib import Path

SCHEMA_SQL = '''
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS research_sessions (
  session_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS analysis_runs (
  run_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  run_name TEXT NOT NULL,
  symbol TEXT NOT NULL,
  data_source TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  strategy_type TEXT NOT NULL,
  strategy_params_json TEXT NOT NULL,
  cost_model_json TEXT NOT NULL,
  initial_capital REAL NOT NULL,
  position_sizing_json TEXT NOT NULL,
  regime_config_json TEXT NOT NULL,
  run_status TEXT NOT NULL DEFAULT 'completed',
  created_at TEXT NOT NULL,
  completed_at TEXT,
  FOREIGN KEY(session_id) REFERENCES research_sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS run_metrics_snapshot (
  run_id TEXT PRIMARY KEY,
  total_return_pct REAL,
  annualized_return_pct REAL,
  annualized_vol_pct REAL,
  sharpe REAL,
  max_drawdown_pct REAL,
  regime_distribution_json TEXT NOT NULL,
  risk_flags_json TEXT NOT NULL,
  computed_at TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES analysis_runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS price_cache (
  symbol TEXT NOT NULL,
  interval TEXT NOT NULL,
  date TEXT NOT NULL,
  open REAL, high REAL, low REAL, close REAL, volume REAL,
  PRIMARY KEY(symbol, interval, date)
);
'''

def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
