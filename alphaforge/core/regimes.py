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
