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
