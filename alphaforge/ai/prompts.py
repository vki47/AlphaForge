from __future__ import annotations

import json
from typing import Any

ROLE = "You are AlphaForge's local quantitative copilot running through Ollama."


def _render(task: str, data: dict[str, Any], instructions: str) -> str:
    return (
        f"{ROLE}\n"
        "Rules:\n"
        "- Only interpret supplied structured values.\n"
        "- Do not invent raw market numbers or hidden assumptions.\n"
        "- If a value is missing, explicitly say it is missing.\n"
        f"Task: {task}\n"
        f"Instructions: {instructions}\n"
        "Structured quant output (JSON):\n"
        f"{json.dumps(data, indent=2, default=str)}\n"
        "Return concise bullet points with practical, risk-aware suggestions."
    )


def market_analysis_prompt(data: dict[str, Any]) -> str:
    return _render(
        task="Market analysis interpretation",
        data=data,
        instructions=(
            "Explain trend, volatility, RSI, and near-term return context. "
            "End with one conservative action idea."
        ),
    )


def strategy_explanation_prompt(data: dict[str, Any]) -> str:
    return _render(
        task="Strategy result explanation",
        data=data,
        instructions=(
            "Explain performance drivers using returns, drawdown, volatility, and Sharpe. "
            "Call out one weakness and one concrete improvement."
        ),
    )


def risk_analysis_prompt(data: dict[str, Any]) -> str:
    return _render(
        task="Portfolio risk explanation",
        data=data,
        instructions=(
            "Explain risk from drawdown, volatility, allocation weights, and correlation summary. "
            "Give two practical risk controls."
        ),
    )


def qa_prompt(question: str, context_data: dict[str, Any]) -> str:
    return _render(
        task=f"Quant Q&A: {question}",
        data=context_data,
        instructions="Answer directly using context only; mention uncertainty when context is insufficient.",
    )
