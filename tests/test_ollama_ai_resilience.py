import io
import json
import urllib.error

import pytest

from alphaforge.ai.ai_service import AIService
from alphaforge.ai.ollama_client import OllamaClient, OllamaClientError


class _FakeResponse:
    def __init__(self, payload: dict[str, str]):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_ai_service_uses_fallback_model_when_primary_fails():
    class _FakeClient:
        def __init__(self):
            self.calls: list[str] = []

        def generate(self, prompt: str, model: str = "phi3") -> str:
            self.calls.append(model)
            if model == "phi3":
                raise OllamaClientError("primary unavailable")
            return f"ok via {model}"

    client = _FakeClient()
    service = AIService(client=client, primary_model="phi3", fallback_model="mistral")

    result = service.generate_market_insight({"symbol": "AAPL"})

    assert result == "ok via mistral"
    assert client.calls == ["phi3", "mistral"]


def test_ollama_client_generate_success_without_network(monkeypatch):
    client = OllamaClient(base_url="http://localhost:11434", timeout_seconds=5)

    def _fake_urlopen(req, timeout):
        assert req.full_url.endswith("/api/generate")
        assert timeout == 5
        return _FakeResponse({"response": " concise answer "})

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    assert client.generate("hello", model="phi3") == "concise answer"


def test_ollama_client_maps_http_error_to_friendly_message(monkeypatch):
    client = OllamaClient()

    def _fake_urlopen(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 500, "boom", hdrs=None, fp=io.BytesIO(b"bad"))

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    with pytest.raises(OllamaClientError, match="HTTP 500"):
        client.generate("hello")


def test_ollama_client_maps_runner_crash_to_actionable_message(monkeypatch):
    client = OllamaClient()

    def _fake_urlopen(req, timeout):
        payload = b'{"error":"llama runner process has terminated: %!w(<nil>)"}'
        raise urllib.error.HTTPError(req.full_url, 500, "boom", hdrs=None, fp=io.BytesIO(payload))

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    with pytest.raises(OllamaClientError, match="runner crashed"):
        client.generate("hello")
