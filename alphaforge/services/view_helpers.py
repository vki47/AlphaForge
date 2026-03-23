from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from alphaforge.utils_config import get_config_root, get_env_path


_NETWORK_ERROR_TOKENS = ("timeout", "connection", "network", "dns", "ssl", "unreachable")
_PROVIDER_ERROR_TOKENS = ("provider", "rate limit", "forbidden", "unauthorized", "api key", "429")


def normalize_symbol(text: str) -> str:
    return text.strip().upper()


def parse_symbol_list(text: str) -> list[str]:
    return [normalize_symbol(symbol) for symbol in text.split(",") if symbol.strip()]


def has_valid_date_range(start: date, end: date) -> bool:
    return isinstance(start, date) and isinstance(end, date) and start < end


def has_valid_symbol_and_date_range(symbol: str, start: date, end: date) -> bool:
    return bool(normalize_symbol(symbol)) and has_valid_date_range(start, end)


def format_service_error(
    error: str,
    *,
    network_message: str,
    provider_message: str,
    fallback_prefix: str,
) -> str:
    text = (error or "").strip()
    lowered = text.lower()
    if any(token in lowered for token in _NETWORK_ERROR_TOKENS):
        return network_message
    if any(token in lowered for token in _PROVIDER_ERROR_TOKENS):
        return provider_message
    return fallback_prefix


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
    start_date: str,
    end_date: str,
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
        f"## Report Header\n"
        f"- **Primary Symbol:** {symbol}\n"
        f"- **Period:** {start_date} to {end_date}\n"
        f"- **Rows analyzed:** {rows_analyzed}\n\n"
        f"## Assumptions\n"
        f"- **Strategy:** MA crossover (long/flat)\n"
        f"- **Execution costs:** commission {commission_bps:.2f} bps, slippage {slippage_bps:.2f} bps\n"
        f"- **Data caveat:** Metrics are based on historical prices and do not guarantee future performance.\n\n"
        f"## Key Stats\n"
        f"- **Latest close:** {latest_close:.2f}\n"
        f"- **Latest RSI:** {latest_rsi:.2f}\n"
        f"- **Latest regime:** {latest_regime}\n"
        f"- **Total Return:** {total_return_pct:.2f}%\n"
        f"- **Annualized Return:** {annualized_return_pct:.2f}%\n"
        f"- **Annualized Volatility:** {annualized_volatility_pct:.2f}%\n"
        f"- **Sharpe:** {sharpe:.3f}\n"
        f"- **Max Drawdown:** {max_drawdown_pct:.2f}%\n"
    )
    if compare_snapshot:
        benchmark_return_pct = float(compare_snapshot["period_return_pct"])
        relative_performance_pct = total_return_pct - benchmark_return_pct
        report += (
            f"\n## Relative Performance vs Benchmark ({compare_snapshot['symbol']})\n"
            f"- **Latest close:** {float(compare_snapshot['latest_close']):.2f}\n"
            f"- **Latest RSI:** {float(compare_snapshot['latest_rsi']):.2f}\n"
            f"- **Latest regime:** {compare_snapshot['latest_regime']}\n"
            f"- **Benchmark Period Return:** {benchmark_return_pct:.2f}%\n"
            f"- **Strategy Relative Return:** {relative_performance_pct:.2f}%\n"
        )
    report += (
        "\n## Risks\n"
        "- Model risk from indicator lag and structural market changes.\n"
        "- Backtest risk from historical bias, survivorship bias, and execution simplifications.\n"
        "- Concentration risk when relying on a single symbol.\n\n"
        "## Action Items\n"
        "- Validate assumptions with out-of-sample testing.\n"
        "- Compare against benchmark and alternate strategy variants.\n"
        "- Review position sizing and risk limits before deployment.\n"
    )
    return report


def has_required_settings_fields(values: dict[str, str]) -> bool:
    return bool(
        values.get("OLLAMA_BASE_URL", "").strip()
        and values.get("OLLAMA_PRIMARY_MODEL", "").strip()
        and values.get("OLLAMA_FALLBACK_MODEL", "").strip()
        and values.get("ALPHAFORGE_DB_PATH", "").strip()
    )


def resolve_env_path(env_target: Path | None = None) -> Path:
    if env_target is None:
        return get_env_path().resolve()
    candidate = env_target.expanduser()
    if candidate.is_dir():
        candidate = candidate / ".env"
    if not candidate.is_absolute():
        candidate = get_config_root() / candidate
    return candidate.resolve()


def write_env_file(env_path: Path, values: dict[str, str]) -> None:
    resolved_path = resolve_env_path(env_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(
        "\n".join([f"{k}={v}" for k, v in values.items()]) + "\n",
        encoding="utf-8",
    )
