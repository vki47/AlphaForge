from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from alphaforge.services.view_helpers import has_required_settings_fields, resolve_env_path, write_env_file
from alphaforge.utils_config import AppConfig, get_config_root, get_env_path


class SettingsView(QWidget):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(QLabel("<h2>Settings</h2>"))
        layout.addWidget(
            QLabel("Edit config and write to local `.env` in project root (restart app to apply).")
        )

        form = QFormLayout()
        self.base_url = QLineEdit(self._config.ollama_base_url)
        self.base_url_error = QLabel("")

        self.primary_model = QLineEdit(self._config.ollama_primary_model)
        self.primary_model_error = QLabel("")

        self.fallback_model = QLineEdit(self._config.ollama_fallback_model)
        self.fallback_model_error = QLabel("")

        self.timeout = QSpinBox()
        self.timeout.setRange(1, 300)
        self.timeout.setValue(int(self._config.ollama_timeout_seconds))

        self.db_path = QLineEdit(str(self._config.db_path))
        self.db_path_error = QLabel("")

        for error_label in [
            self.base_url_error,
            self.primary_model_error,
            self.fallback_model_error,
            self.db_path_error,
        ]:
            error_label.setStyleSheet("color: #b00020;")

        form.addRow("OLLAMA_BASE_URL", self._with_inline_error(self.base_url, self.base_url_error))
        form.addRow(
            "OLLAMA_PRIMARY_MODEL",
            self._with_inline_error(self.primary_model, self.primary_model_error),
        )
        form.addRow(
            "OLLAMA_FALLBACK_MODEL",
            self._with_inline_error(self.fallback_model, self.fallback_model_error),
        )
        form.addRow("OLLAMA_TIMEOUT_SECONDS", self.timeout)
        form.addRow("ALPHAFORGE_DB_PATH", self._with_inline_error(self.db_path, self.db_path_error))
        layout.addLayout(form)

        controls = QHBoxLayout()
        save_btn = QPushButton("Save .env")
        save_btn.clicked.connect(self.save_env)
        test_btn = QPushButton("Test Ollama Connection")
        test_btn.clicked.connect(self.test_connection)
        self.msg = QLabel("Status: Ready")
        controls.addWidget(save_btn)
        controls.addWidget(test_btn)
        controls.addWidget(self.msg, 1)
        controls.addStretch(1)
        layout.addLayout(controls)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Tip: click Save .env, then restart AlphaForge to load new values."
            f"\nConfig root: {get_config_root()}"
            f"\n.env path: {get_env_path()}"
        )
        layout.addWidget(text)

    def save_env(self) -> None:
        values = self._env_values()
        ok, message = self._validate_settings(values)
        if not ok:
            self._set_status(message, success=False)
            return

        env_path = self._resolve_env_path()
        self._write_env_file(env_path, values)
        self._set_status(f"Saved settings to {env_path}. Restart AlphaForge to apply.", success=True)

    def _env_values(self) -> dict[str, str]:
        return {
            "OLLAMA_BASE_URL": self.base_url.text().strip(),
            "OLLAMA_PRIMARY_MODEL": self.primary_model.text().strip(),
            "OLLAMA_FALLBACK_MODEL": self.fallback_model.text().strip(),
            "OLLAMA_TIMEOUT_SECONDS": str(int(self.timeout.value())),
            "ALPHAFORGE_DB_PATH": self.db_path.text().strip(),
        }

    @staticmethod
    def _has_required_fields(values: dict[str, str]) -> bool:
        return has_required_settings_fields(values)

    @staticmethod
    def _resolve_env_path() -> Path:
        return resolve_env_path()

    @staticmethod
    def _write_env_file(env_path: Path, values: dict[str, str]) -> None:
        write_env_file(env_path, values)

    @staticmethod
    def _with_inline_error(field: QWidget, error_label: QLabel) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(field)
        layout.addWidget(error_label)
        return wrapper

    @staticmethod
    def _is_valid_ollama_url(value: str) -> bool:
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            return False
        if not parsed.netloc or re.search(r"\s", parsed.netloc):
            return False
        if parsed.path not in {"", "/"}:
            return False
        return True

    def _clear_errors(self) -> None:
        for label in [
            self.base_url_error,
            self.primary_model_error,
            self.fallback_model_error,
            self.db_path_error,
        ]:
            label.setText("")

    def _validate_settings(self, values: dict[str, str]) -> tuple[bool, str]:
        self._clear_errors()
        if not self._has_required_fields(values):
            if not values["OLLAMA_BASE_URL"]:
                self.base_url_error.setText("Required: enter an Ollama base URL.")
            if not values["OLLAMA_PRIMARY_MODEL"]:
                self.primary_model_error.setText("Required: enter a primary model name.")
            if not values["OLLAMA_FALLBACK_MODEL"]:
                self.fallback_model_error.setText("Required: enter a fallback model name.")
            if not values["ALPHAFORGE_DB_PATH"]:
                self.db_path_error.setText("Required: enter a database path.")
            return False, "Fix required fields before saving."

        if not self._is_valid_ollama_url(values["OLLAMA_BASE_URL"]):
            self.base_url_error.setText(
                "Invalid URL. Use http(s)://host[:port] (example: http://localhost:11434)."
            )
            return False, "Invalid OLLAMA_BASE_URL."

        db_path = Path(values["ALPHAFORGE_DB_PATH"]).expanduser()
        if not str(db_path):
            self.db_path_error.setText("Database path cannot be empty.")
            return False, "Invalid ALPHAFORGE_DB_PATH."

        return True, "OK"

    def _set_status(self, text: str, *, success: bool) -> None:
        color = "#1b5e20" if success else "#b00020"
        self.msg.setStyleSheet(f"color: {color};")
        self.msg.setText(f"Status: {text}")

    def test_connection(self) -> None:
        values = self._env_values()
        ok, message = self._validate_settings(values)
        if not ok:
            self._set_status(message, success=False)
            return

        base_url = values["OLLAMA_BASE_URL"].rstrip("/")
        primary_model = values["OLLAMA_PRIMARY_MODEL"]
        timeout_seconds = max(2, int(self.timeout.value()))
        version_payload = {}
        try:
            req = urllib.request.Request(
                f"{base_url}/api/version",
                headers={"Accept": "application/json"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                version_payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            self._set_status(f"Connection failed: HTTP {exc.code} from Ollama.", success=False)
            return
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            self._set_status(f"Connection failed: {exc}.", success=False)
            return
        except json.JSONDecodeError:
            self._set_status("Connection failed: invalid JSON from Ollama.", success=False)
            return

        server_version = str(version_payload.get("version", "unknown")).strip() or "unknown"

        try:
            req = urllib.request.Request(
                f"{base_url}/api/tags",
                headers={"Accept": "application/json"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in payload.get("models", []) if isinstance(m, dict)]
            has_primary = primary_model in models or any(
                name.startswith(f"{primary_model}:") for name in models
            )
            if not has_primary:
                self._set_status(
                    f"Ollama reachable (v{server_version}), but primary model '{primary_model}' is unavailable.",
                    success=False,
                )
                return
            self._set_status(
                f"Ollama reachable (v{server_version}). Primary model '{primary_model}' is available.",
                success=True,
            )
            return
        except Exception:
            pass

        try:
            generate_req = urllib.request.Request(
                f"{base_url}/api/generate",
                data=json.dumps(
                    {
                        "model": primary_model,
                        "prompt": "ping",
                        "stream": False,
                    }
                ).encode("utf-8"),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(generate_req, timeout=timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if payload.get("error"):
                self._set_status(
                    f"Ollama reachable (v{server_version}), but model test failed: {payload['error']}",
                    success=False,
                )
                return
        except urllib.error.HTTPError as exc:
            self._set_status(
                f"Ollama reachable (v{server_version}), but model test failed with HTTP {exc.code}.",
                success=False,
            )
            return
        except Exception as exc:
            self._set_status(
                f"Ollama reachable (v{server_version}), but model test failed: {exc}.",
                success=False,
            )
            return

        self._set_status(
            f"Ollama reachable (v{server_version}). Primary model '{primary_model}' passed generation test.",
            success=True,
        )
