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
