from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass


class OllamaClientError(RuntimeError):
    """Raised when the local Ollama API returns an error or invalid payload."""


@dataclass(frozen=True)
class OllamaClient:
    base_url: str = "http://localhost:11434"
    timeout_seconds: int = 25

    def generate(self, prompt: str, model: str = "phi3") -> str:
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
            raise OllamaClientError(f"Ollama request failed with HTTP {exc.code}.") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise OllamaClientError("Ollama request timed out. Try a shorter query or retry.") from exc
        except urllib.error.URLError as exc:
            raise OllamaClientError(
                "Could not reach local Ollama. Ensure Ollama is running at http://localhost:11434."
            ) from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise OllamaClientError("Ollama returned an invalid JSON response.") from exc

        text = parsed.get("response")
        if not isinstance(text, str) or not text.strip():
            raise OllamaClientError("Ollama returned an empty response.")
        return text.strip()
