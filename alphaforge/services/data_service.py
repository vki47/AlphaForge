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
