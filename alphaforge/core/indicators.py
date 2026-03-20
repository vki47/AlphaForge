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
