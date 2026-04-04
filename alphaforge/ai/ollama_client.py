from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass


class OllamaClientError(RuntimeError):
    """Raised when the local Ollama API returns an error or invalid payload."""


def _friendly_http_500(detail: str) -> str | None:
    text = detail.lower()
    if "llama runner process has terminated" in text:
        return (
            "Ollama model runner crashed while generating. "
            "This is usually a local memory/VRAM issue or a stale runner process. "
            "Try: `ollama ps`, then restart with `ollama stop <model>` and retry, "
            "or select a smaller model in Settings."
        )
    return None


@dataclass(frozen=True)
class OllamaClient:
    base_url: str = "http://localhost:11434"
    timeout_seconds: int = 25

    def generate(self, prompt: str, model: str = "phi3") -> str:
        if not prompt.strip():
            raise OllamaClientError("Prompt is empty. Provide structured context before asking AI.")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        req = urllib.request.Request(
            url=f"{self.base_url.rstrip('/')}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            if exc.code == 500:
                friendly_500 = _friendly_http_500(detail)
                if friendly_500:
                    raise OllamaClientError(friendly_500) from exc
            message = f"Ollama request failed with HTTP {exc.code}."
            if detail:
                message += f" Details: {detail[:160]}"
            raise OllamaClientError(message) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise OllamaClientError(
                "Ollama request timed out. Try a shorter query, lighter prompt, or a smaller model."
            ) from exc
        except urllib.error.URLError as exc:
            reason = str(getattr(exc, "reason", "")).lower()
            if "refused" in reason or "failed to establish" in reason:
                raise OllamaClientError(
                    "Cannot connect to Ollama at http://localhost:11434. Start Ollama with `ollama serve` and retry."
                ) from exc
            raise OllamaClientError(
                "Could not reach local Ollama. Ensure Ollama is running at http://localhost:11434."
            ) from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise OllamaClientError("Ollama returned invalid JSON.") from exc

        if parsed.get("error"):
            raise OllamaClientError(f"Ollama error: {parsed['error']}")

        text = parsed.get("response")
        if not isinstance(text, str) or not text.strip():
            raise OllamaClientError("Ollama returned an empty response.")
        return text.strip()
