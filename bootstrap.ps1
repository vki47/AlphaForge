# AlphaForge bootstrap (Windows PowerShell)
$ErrorActionPreference = "Stop"

# ---------- folders ----------
$dirs = @(
  "alphaforge",
  "alphaforge\ai",
  "alphaforge\core",
  "alphaforge\data",
  "alphaforge\data\providers",
  "alphaforge\services",
  "alphaforge\ui",
  "alphaforge\ui\views"
)
$dirs | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }

# ---------- root files ----------
@"
.env
__pycache__/
*.py[cod]
data/*.db
"@ | Set-Content .gitignore -Encoding UTF8

@"
OPENAI_API_KEY=
GEMINI_API_KEY=
DEFAULT_AI_PROVIDER=openai
OPENAI_MODEL=gpt-4.1-mini
GEMINI_MODEL=gemini-1.5-pro
ALPHAFORGE_DB_PATH=data/alphaforge.db
"@ | Set-Content .env.example -Encoding UTF8

@"
PySide6>=6.7
pandas>=2.2
numpy>=1.26
python-dotenv>=1.0
yfinance>=0.2.50
"@ | Set-Content requirements.txt -Encoding UTF8

@"
from alphaforge.ui.main_window import run_app

if __name__ == "__main__":
    run_app()
"@ | Set-Content app.py -Encoding UTF8

@"
# AlphaForge

Native desktop (PySide6) AI-assisted quant research app.

## Quick start
1. python -m venv .venv
2. .\.venv\Scripts\Activate.ps1
3. pip install -r requirements.txt
4. Copy .env.example to .env and fill keys
5. python app.py
"@ | Set-Content README.md -Encoding UTF8

# ---------- package markers ----------
"" | Set-Content alphaforge\__init__.py -Encoding UTF8
"" | Set-Content alphaforge\ai\__init__.py -Encoding UTF8
"" | Set-Content alphaforge\core\__init__.py -Encoding UTF8
"" | Set-Content alphaforge\data\__init__.py -Encoding UTF8
"" | Set-Content alphaforge\data\providers\__init__.py -Encoding UTF8
"" | Set-Content alphaforge\services\__init__.py -Encoding UTF8
"" | Set-Content alphaforge\ui\__init__.py -Encoding UTF8
"" | Set-Content alphaforge\ui\views\__init__.py -Encoding UTF8

# ---------- utils ----------
@"
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
"@ | Set-Content alphaforge\utils_config.py -Encoding UTF8

@"
import logging
def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
"@ | Set-Content alphaforge\utils_logger.py -Encoding UTF8

# ---------- db ----------
@"
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
"@ | Set-Content alphaforge\data\db.py -Encoding UTF8

# ---------- provider ----------
@"
from __future__ import annotations
from datetime import date
import pandas as pd
import yfinance as yf

class YFinanceProvider:
    def fetch_ohlcv(self, symbol: str, start: date, end: date, interval: str = "1d") -> pd.DataFrame:
        data = yf.Ticker(symbol).history(start=start.isoformat(), end=end.isoformat(), interval=interval, auto_adjust=False)
        if data.empty:
            return pd.DataFrame(columns=["Date","Open","High","Low","Close","Volume"])
        frame = data.reset_index().copy()
        if "Datetime" in frame.columns:
            frame.rename(columns={"Datetime":"Date"}, inplace=True)
        frame["Date"] = pd.to_datetime(frame["Date"]).dt.tz_localize(None)
        return frame[[c for c in ["Date","Open","High","Low","Close","Volume"] if c in frame.columns]]
"@ | Set-Content alphaforge\data\providers\yfinance_provider.py -Encoding UTF8

# ---------- core ----------
@"
from __future__ import annotations
import pandas as pd

def compute_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    d = frame.copy().sort_values("Date").reset_index(drop=True)
    d["return"] = d["Close"].pct_change().fillna(0.0)
    d["ma_fast"] = d["Close"].rolling(20, min_periods=1).mean()
    d["ma_slow"] = d["Close"].rolling(50, min_periods=1).mean()
    delta = d["Close"].diff().fillna(0.0)
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    rs = up.rolling(14, min_periods=1).mean() / down.rolling(14, min_periods=1).mean().replace(0.0, 1e-9)
    d["rsi"] = 100.0 - (100.0 / (1.0 + rs))
    d["volatility"] = d["return"].rolling(20, min_periods=2).std().fillna(0.0) * (252**0.5)
    return d
"@ | Set-Content alphaforge\core\indicators.py -Encoding UTF8

@"
from __future__ import annotations
import pandas as pd

def classify_regime(frame: pd.DataFrame, vol_quantile: float = 0.8) -> pd.DataFrame:
    d = frame.copy()
    th = d["volatility"].quantile(vol_quantile) if len(d) else 0.0
    def label(r: pd.Series) -> str:
        up = r["ma_fast"] > r["ma_slow"]
        dn = r["ma_fast"] < r["ma_slow"]
        hv = r["volatility"] >= th
        if hv and up: return "high_vol_uptrend"
        if hv and dn: return "high_vol_downtrend"
        if up: return "uptrend"
        if dn: return "downtrend"
        return "range"
    d["regime"] = d.apply(label, axis=1)
    return d
"@ | Set-Content alphaforge\core\regimes.py -Encoding UTF8

@"
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

@dataclass
class BacktestResult:
    frame: pd.DataFrame
    total_return_pct: float
    annualized_return_pct: float
    annualized_vol_pct: float
    sharpe: float
    max_drawdown_pct: float

def run_ma_crossover_backtest(frame: pd.DataFrame, commission_bps: float = 5.0, slippage_bps: float = 3.0) -> BacktestResult:
    d = frame.copy().sort_values("Date").reset_index(drop=True)
    d["signal"] = (d["ma_fast"] > d["ma_slow"]).astype(int)
    d["position"] = d["signal"].shift(1).fillna(0)
    d["strategy_return_gross"] = d["position"] * d["return"]
    turnover = (d["position"] - d["position"].shift(1).fillna(0)).abs()
    d["cost"] = turnover * ((commission_bps + slippage_bps) / 10000.0)
    d["strategy_return_net"] = d["strategy_return_gross"] - d["cost"]
    d["equity_curve"] = (1.0 + d["strategy_return_net"]).cumprod()
    dd = d["equity_curve"] / d["equity_curve"].cummax() - 1.0
    tr = (d["equity_curve"].iloc[-1] - 1.0) if len(d) else 0.0
    ar = ((1.0 + tr) ** (252 / max(len(d), 1)) - 1.0) if len(d) else 0.0
    av = d["strategy_return_net"].std() * (252**0.5) if len(d) > 1 else 0.0
    sh = ar / av if av > 1e-9 else 0.0
    md = dd.min() if len(dd) else 0.0
    return BacktestResult(d, tr*100, ar*100, av*100, sh, md*100)
"@ | Set-Content alphaforge\core\backtester.py -Encoding UTF8

# ---------- services ----------
@"
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import pandas as pd
from alphaforge.data.providers.yfinance_provider import YFinanceProvider

@dataclass
class DataFetchResult:
    frame: pd.DataFrame
    source: str
    symbol: str
    start: date
    end: date
    interval: str

class DataService:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._provider = YFinanceProvider()

    def fetch(self, symbol: str, start: date, end: date, interval: str = "1d") -> DataFetchResult:
        f = self._provider.fetch_ohlcv(symbol, start, end, interval)
        self._cache(symbol, interval, f)
        return DataFetchResult(f, "yfinance", symbol, start, end, interval)

    def _cache(self, symbol: str, interval: str, frame: pd.DataFrame) -> None:
        if frame.empty: return
        rows = []
        for _, r in frame.iterrows():
            rows.append((symbol.upper(), interval, pd.Timestamp(r["Date"]).date().isoformat(),
                        float(r.get("Open",0)), float(r.get("High",0)), float(r.get("Low",0)),
                        float(r.get("Close",0)), float(r.get("Volume",0))))
        with sqlite3.connect(self._db_path) as c:
            c.executemany("""INSERT INTO price_cache(symbol,interval,date,open,high,low,close,volume)
                             VALUES (?,?,?,?,?,?,?,?)
                             ON CONFLICT(symbol,interval,date) DO UPDATE SET
                             open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,volume=excluded.volume""", rows)
            c.commit()
"@ | Set-Content alphaforge\services\data_service.py -Encoding UTF8

@"
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import pandas as pd
from alphaforge.core.indicators import compute_indicators
from alphaforge.core.regimes import classify_regime
from alphaforge.services.data_service import DataService

@dataclass
class AnalysisResult:
    frame: pd.DataFrame

class AnalysisService:
    def __init__(self, data_service: DataService) -> None:
        self._data_service = data_service

    def run(self, symbol: str, start: date, end: date) -> AnalysisResult:
        raw = self._data_service.fetch(symbol, start, end).frame
        return AnalysisResult(classify_regime(compute_indicators(raw)))
"@ | Set-Content alphaforge\services\analysis_service.py -Encoding UTF8

@"
from __future__ import annotations
from datetime import date
from alphaforge.core.backtester import run_ma_crossover_backtest
from alphaforge.services.analysis_service import AnalysisService

class BacktestService:
    def __init__(self, analysis_service: AnalysisService) -> None:
        self._analysis_service = analysis_service

    def run_ma(self, symbol: str, start: date, end: date, commission_bps: float, slippage_bps: float):
        a = self._analysis_service.run(symbol, start, end)
        return run_ma_crossover_backtest(a.frame, commission_bps, slippage_bps)
"@ | Set-Content alphaforge\services\backtest_service.py -Encoding UTF8

@"
from alphaforge.data.db import init_db
from alphaforge.utils_config import load_config
from alphaforge.utils_logger import setup_logging

def bootstrap():
    setup_logging()
    c = load_config()
    init_db(c.db_path)
    return c
"@ | Set-Content alphaforge\services\bootstrap.py -Encoding UTF8

# ---------- UI ----------
@"
from __future__ import annotations
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QListWidget, QListWidgetItem, QMainWindow, QStackedWidget, QHBoxLayout, QVBoxLayout, QWidget, QToolBar
from alphaforge.services.bootstrap import bootstrap
from alphaforge.services.data_service import DataService
from alphaforge.services.analysis_service import AnalysisService
from alphaforge.services.backtest_service import BacktestService
from alphaforge.ui.views.data_view import DataView
from alphaforge.ui.views.indicators_regime_view import IndicatorsRegimeView
from alphaforge.ui.views.backtest_view import BacktestView
from alphaforge.ui.views.placeholders import PlaceholderView

class MainWindow(QMainWindow):
    NAV_ITEMS = ["Dashboard","Data","Indicators & Regime","Backtest","Portfolio Risk","Run Compare","Research Report","Settings"]
    def __init__(self, data_service, analysis_service, backtest_service):
        super().__init__()
        self._data_service = data_service
        self._analysis_service = analysis_service
        self._backtest_service = backtest_service
        self.setWindowTitle("AlphaForge — AI Quant Research Copilot")
        self.resize(1200, 780)

        tb = QToolBar("Top")
        tb.setMovable(False)
        tb.addWidget(QLabel("Symbol/Date controls will appear per module"))
        self.addToolBar(Qt.TopToolBarArea, tb)

        root = QWidget(); layout = QVBoxLayout(root)
        nav = QListWidget(); nav.setMaximumWidth(250)
        pages = QStackedWidget()
        for n in self.NAV_ITEMS:
            nav.addItem(QListWidgetItem(n))
            if n == "Data":
                pages.addWidget(DataView(self._data_service))
            elif n == "Indicators & Regime":
                pages.addWidget(IndicatorsRegimeView(self._analysis_service))
            elif n == "Backtest":
                pages.addWidget(BacktestView(self._backtest_service))
            else:
                pages.addWidget(PlaceholderView(n, f"{n} coming next..."))
        nav.currentRowChanged.connect(pages.setCurrentIndex)
        nav.setCurrentRow(0)

        row = QHBoxLayout(); row.addWidget(nav); row.addWidget(pages, 1)
        layout.addLayout(row)
        self.setCentralWidget(root)

def run_app():
    cfg = bootstrap()
    ds = DataService(cfg.db_path)
    an = AnalysisService(ds)
    bt = BacktestService(an)
    app = QApplication(sys.argv)
    w = MainWindow(ds, an, bt)
    w.show()
    sys.exit(app.exec())
"@ | Set-Content alphaforge\ui\main_window.py -Encoding UTF8

@"
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
class PlaceholderView(QWidget):
    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        l = QVBoxLayout(self)
        l.addWidget(QLabel(f"<h2>{title}</h2>"))
        b = QLabel(subtitle); b.setWordWrap(True)
        l.addWidget(b); l.addStretch()
"@ | Set-Content alphaforge\ui\views\placeholders.py -Encoding UTF8

@"
from __future__ import annotations
from datetime import date
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
from alphaforge.services.data_service import DataService

class DataView(QWidget):
    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent); self._s=data_service; self._build()
    def _build(self):
        l=QVBoxLayout(self); f=QFormLayout()
        self.sym=QLineEdit("AAPL"); self.st=QDateEdit(QDate(2024,1,1)); self.en=QDateEdit(QDate.currentDate())
        self.st.setCalendarPopup(True); self.en.setCalendarPopup(True)
        f.addRow("Symbol",self.sym); f.addRow("Start",self.st); f.addRow("End",self.en); l.addLayout(f)
        a=QHBoxLayout(); self.btn=QPushButton("Fetch Data"); self.btn.clicked.connect(self.fetch); self.msg=QLabel("Ready")
        a.addWidget(self.btn); a.addWidget(self.msg,1); l.addLayout(a)
        self.t=QTableWidget(0,6); self.t.setHorizontalHeaderLabels(["Date","Open","High","Low","Close","Volume"]); l.addWidget(self.t)
    def fetch(self):
        s=self.sym.text().strip().upper(); st=self.st.date().toPython(); en=self.en.date().toPython()
        if not s or not isinstance(st,date) or not isinstance(en,date) or st>=en: self.msg.setText("Invalid input"); return
        try:
            r=self._s.fetch(s,st,en); f=r.frame; self.t.setRowCount(len(f))
            for i,(_,x) in enumerate(f.iterrows()):
                self.t.setItem(i,0,QTableWidgetItem(str(x.get("Date",""))))
                self.t.setItem(i,1,QTableWidgetItem(f"{x.get('Open',0):.2f}"))
                self.t.setItem(i,2,QTableWidgetItem(f"{x.get('High',0):.2f}"))
                self.t.setItem(i,3,QTableWidgetItem(f"{x.get('Low',0):.2f}"))
                self.t.setItem(i,4,QTableWidgetItem(f"{x.get('Close',0):.2f}"))
                self.t.setItem(i,5,QTableWidgetItem(f"{x.get('Volume',0):.0f}"))
            self.msg.setText(f"Loaded {len(f)} rows")
        except Exception as e:
            self.msg.setText(f"Error: {e}")
"@ | Set-Content alphaforge\ui\views\data_view.py -Encoding UTF8

@"
from __future__ import annotations
from datetime import date
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
from alphaforge.services.analysis_service import AnalysisService

class IndicatorsRegimeView(QWidget):
    def __init__(self, analysis_service: AnalysisService, parent=None):
        super().__init__(parent); self._s=analysis_service; self._build()
    def _build(self):
        l=QVBoxLayout(self); f=QFormLayout()
        self.sym=QLineEdit("AAPL"); self.st=QDateEdit(QDate(2024,1,1)); self.en=QDateEdit(QDate.currentDate())
        self.st.setCalendarPopup(True); self.en.setCalendarPopup(True)
        f.addRow("Symbol",self.sym); f.addRow("Start",self.st); f.addRow("End",self.en); l.addLayout(f)
        a=QHBoxLayout(); self.btn=QPushButton("Compute"); self.btn.clicked.connect(self.run); self.msg=QLabel("Ready")
        a.addWidget(self.btn); a.addWidget(self.msg,1); l.addLayout(a)
        self.t=QTableWidget(0,6); self.t.setHorizontalHeaderLabels(["Date","Close","MA Fast","MA Slow","RSI","Regime"]); l.addWidget(self.t)
    def run(self):
        s=self.sym.text().strip().upper(); st=self.st.date().toPython(); en=self.en.date().toPython()
        if not s or not isinstance(st,date) or not isinstance(en,date) or st>=en: self.msg.setText("Invalid input"); return
        r=self._s.run(s,st,en).frame.tail(120).reset_index(drop=True); self.t.setRowCount(len(r))
        for i,(_,x) in enumerate(r.iterrows()):
            self.t.setItem(i,0,QTableWidgetItem(str(x.get("Date",""))))
            self.t.setItem(i,1,QTableWidgetItem(f"{x.get('Close',0):.2f}"))
            self.t.setItem(i,2,QTableWidgetItem(f"{x.get('ma_fast',0):.2f}"))
            self.t.setItem(i,3,QTableWidgetItem(f"{x.get('ma_slow',0):.2f}"))
            self.t.setItem(i,4,QTableWidgetItem(f"{x.get('rsi',0):.2f}"))
            self.t.setItem(i,5,QTableWidgetItem(str(x.get("regime",""))))
        self.msg.setText(f"Computed {len(r)} rows")
"@ | Set-Content alphaforge\ui\views\indicators_regime_view.py -Encoding UTF8

@"
from __future__ import annotations
from datetime import date
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit,QDoubleSpinBox,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QTextEdit,QVBoxLayout,QWidget
from alphaforge.services.backtest_service import BacktestService

class BacktestView(QWidget):
    def __init__(self, backtest_service: BacktestService, parent=None):
        super().__init__(parent); self._s=backtest_service; self._build()
    def _build(self):
        l=QVBoxLayout(self); f=QFormLayout()
        self.sym=QLineEdit("AAPL"); self.st=QDateEdit(QDate(2024,1,1)); self.en=QDateEdit(QDate.currentDate())
        self.st.setCalendarPopup(True); self.en.setCalendarPopup(True)
        self.c=QDoubleSpinBox(); self.c.setRange(0,200); self.c.setValue(5); self.c.setSuffix(" bps")
        self.sl=QDoubleSpinBox(); self.sl.setRange(0,200); self.sl.setValue(3); self.sl.setSuffix(" bps")
        f.addRow("Symbol",self.sym); f.addRow("Start",self.st); f.addRow("End",self.en); f.addRow("Commission",self.c); f.addRow("Slippage",self.sl)
        l.addLayout(f)
        a=QHBoxLayout(); self.btn=QPushButton("Run MA Backtest"); self.btn.clicked.connect(self.run); self.msg=QLabel("Ready")
        a.addWidget(self.btn); a.addWidget(self.msg,1); l.addLayout(a)
        self.out=QTextEdit(); self.out.setReadOnly(True); l.addWidget(self.out)
    def run(self):
        s=self.sym.text().strip().upper(); st=self.st.date().toPython(); en=self.en.date().toPython()
        if not s or not isinstance(st,date) or not isinstance(en,date) or st>=en: self.msg.setText("Invalid input"); return
        r=self._s.run_ma(s,st,en,float(self.c.value()),float(self.sl.value()))
        self.out.setPlainText(
            f"Total Return: {r.total_return_pct:.2f}%\n"
            f"Annualized Return: {r.annualized_return_pct:.2f}%\n"
            f"Annualized Volatility: {r.annualized_vol_pct:.2f}%\n"
            f"Sharpe: {r.sharpe:.3f}\n"
            f"Max Drawdown: {r.max_drawdown_pct:.2f}%"
        )
        self.msg.setText("Backtest complete")
"@ | Set-Content alphaforge\ui\views\backtest_view.py -Encoding UTF8

Write-Host "✅ Bootstrap complete."
Write-Host "Next: python -m venv .venv ; .\\.venv\\Scripts\\Activate.ps1 ; pip install -r requirements.txt ; python app.py"
