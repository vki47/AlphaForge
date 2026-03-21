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


def run_compare_metrics(frame: pd.DataFrame) -> tuple[float, float, float]:
    returns = frame["Close"].pct_change().dropna()
    total_ret = float((frame["Close"].iloc[-1] / frame["Close"].iloc[0] - 1.0) * 100)
    ann_ret = float(returns.mean() * 252 * 100) if not returns.empty else 0.0
    ann_vol = float(returns.std() * (252**0.5) * 100) if len(returns) > 1 else 0.0
    return total_ret, ann_ret, ann_vol


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
