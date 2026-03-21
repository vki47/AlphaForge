from __future__ import annotations

import json
from typing import Any

ROLE = "You are a quantitative finance assistant."


def _render(task: str, data: dict[str, Any], instructions: str) -> str:
    return (
        f"{ROLE}\n"
        "You must only interpret the provided data. Never invent raw values.\n"
        f"Task: {task}\n"
        f"Instructions: {instructions}\n"
        "Structured data (JSON):\n"
        f"{json.dumps(data, indent=2, default=str)}\n"
        "Return concise, practical bullet points."
    )


def market_analysis_prompt(data: dict[str, Any]) -> str:
    return _render(
        task="Analyze current market conditions for this symbol.",
        data=data,
        instructions="Summarize trend, momentum, volatility/regime, and one cautious next step.",
    )


def strategy_explanation_prompt(data: dict[str, Any]) -> str:
    return _render(
        task="Explain strategy behavior and outcomes.",
        data=data,
        instructions="State what likely drove returns, where drawdowns came from, and one improvement idea.",
    )


def risk_analysis_prompt(data: dict[str, Any]) -> str:
    return _render(
        task="Analyze portfolio risk.",
        data=data,
        instructions="Identify key risk drivers, risk level, and two risk-control actions.",
    )


def qa_prompt(question: str, context_data: dict[str, Any]) -> str:
    return _render(
        task=f"Answer user question: {question}",
        data=context_data,
        instructions="Answer directly, reference only supplied context, and note uncertainty if context is missing.",
    )
