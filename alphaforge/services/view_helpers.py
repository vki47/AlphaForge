from __future__ import annotations

from pathlib import Path

import pandas as pd


def parse_allocations(text: str) -> dict[str, float]:
    items = [x.strip() for x in text.split(",") if x.strip()]
    parsed: dict[str, float] = {}
    for item in items:
        if ":" not in item:
            return {}
        symbol, weight_text = item.split(":", 1)
        symbol = symbol.strip().upper()
        try:
            weight = float(weight_text.strip())
        except ValueError:
            return {}
        if not symbol or weight <= 0:
            return {}
        parsed[symbol] = weight
    return parsed


def correlation_summary(corr: pd.DataFrame) -> dict:
    if corr.empty or len(corr.columns) < 2:
        return {"average_pairwise_corr": 0.0, "top_pair": "N/A", "top_pair_corr": 0.0}

    pairs: list[tuple[str, str, float]] = []
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            pairs.append((cols[i], cols[j], float(corr.iloc[i, j])))
    avg_corr = sum(x[2] for x in pairs) / len(pairs)
    top = max(pairs, key=lambda x: x[2])
    return {
        "average_pairwise_corr": avg_corr,
        "top_pair": f"{top[0]}-{top[1]}",
        "top_pair_corr": top[2],
    }


def run_compare_metrics(frame: pd.DataFrame) -> tuple[float, float, float, float, float]:
    returns = frame["Close"].pct_change().dropna()
    total_ret = float((frame["Close"].iloc[-1] / frame["Close"].iloc[0] - 1.0) * 100)
    ann_ret = float(returns.mean() * 252 * 100) if not returns.empty else 0.0
    ann_vol = float(returns.std() * (252**0.5) * 100) if len(returns) > 1 else 0.0
    sharpe = float((ann_ret / ann_vol) if ann_vol > 1e-9 else 0.0)
    if returns.empty:
        max_drawdown = 0.0
    else:
        equity_curve = (1.0 + returns).cumprod()
        drawdown = equity_curve / equity_curve.cummax() - 1.0
        max_drawdown = float(drawdown.min() * 100)
    return total_ret, ann_ret, ann_vol, sharpe, max_drawdown


def build_research_report_markdown(
    symbol: str,
    rows_analyzed: int,
    latest_close: float,
    latest_rsi: float,
    latest_regime: str,
    commission_bps: float,
    slippage_bps: float,
    total_return_pct: float,
    annualized_return_pct: float,
    annualized_volatility_pct: float,
    sharpe: float,
    max_drawdown_pct: float,
    compare_snapshot: dict[str, str | float] | None = None,
) -> str:
    report = (
        f"# Research Report — {symbol}\n\n"
        f"## 1) Market Snapshot\n"
        f"- **Rows analyzed:** {rows_analyzed}\n"
        f"- **Latest close:** {latest_close:.2f}\n"
        f"- **Latest RSI:** {latest_rsi:.2f}\n"
        f"- **Latest regime:** {latest_regime}\n\n"
        f"## 2) MA Crossover Backtest\n"
        f"- **Execution assumptions:** commission {commission_bps:.2f} bps, slippage {slippage_bps:.2f} bps\n"
        f"- **Total Return:** {total_return_pct:.2f}%\n"
        f"- **Annualized Return:** {annualized_return_pct:.2f}%\n"
        f"- **Annualized Volatility:** {annualized_volatility_pct:.2f}%\n"
        f"- **Sharpe:** {sharpe:.3f}\n"
        f"- **Max Drawdown:** {max_drawdown_pct:.2f}%\n"
    )
    if compare_snapshot:
        report += (
            f"\n## 3) Optional Compare Symbol ({compare_snapshot['symbol']})\n"
            f"- **Latest close:** {float(compare_snapshot['latest_close']):.2f}\n"
            f"- **Latest RSI:** {float(compare_snapshot['latest_rsi']):.2f}\n"
            f"- **Latest regime:** {compare_snapshot['latest_regime']}\n"
            f"- **Period Return:** {float(compare_snapshot['period_return_pct']):.2f}%\n"
        )
    return report


def has_required_settings_fields(values: dict[str, str]) -> bool:
    return bool(
        values.get("OLLAMA_BASE_URL")
        and values.get("OLLAMA_PRIMARY_MODEL")
        and values.get("ALPHAFORGE_DB_PATH")
    )


def resolve_env_path(base_dir: Path | None = None) -> Path:
    return (base_dir or Path.cwd()) / ".env"


def write_env_file(env_path: Path, values: dict[str, str]) -> None:
    env_path.write_text("\n".join([f"{k}={v}" for k, v in values.items()]) + "\n", encoding="utf-8")
