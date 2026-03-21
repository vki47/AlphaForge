from __future__ import annotations

from dataclasses import dataclass

from alphaforge.ai.ollama_client import OllamaClient, OllamaClientError
from alphaforge.ai.prompts import (
    market_analysis_prompt,
    qa_prompt,
    risk_analysis_prompt,
    strategy_explanation_prompt,
)


@dataclass(frozen=True)
class AIService:
    client: OllamaClient
    primary_model: str = "phi3"
    fallback_model: str = "mistral"

    def generate_market_insight(self, data: dict) -> str:
        return self._generate_with_fallback(market_analysis_prompt(data))

    def explain_strategy(self, result: dict) -> str:
        return self._generate_with_fallback(strategy_explanation_prompt(result))

    def analyze_portfolio(self, risk_data: dict) -> str:
        return self._generate_with_fallback(risk_analysis_prompt(risk_data))

    def chat(self, question: str, context_data: dict) -> str:
        return self._generate_with_fallback(qa_prompt(question, context_data))

    def _generate_with_fallback(self, prompt: str) -> str:
        first_error: Exception | None = None
        for model in (self.primary_model, self.fallback_model):
            try:
                return self.client.generate(prompt, model=model)
            except OllamaClientError as exc:
                if first_error is None:
                    first_error = exc
        raise OllamaClientError(str(first_error) if first_error else "AI generation failed.")
