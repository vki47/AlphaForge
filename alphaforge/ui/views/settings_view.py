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

from alphaforge.utils_config import AppConfig, get_config_root, get_env_path

MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]+$")


class SettingsView(QWidget):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
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
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self.test_connection)
        self.msg = QLabel("Ready")
        controls.addWidget(save_btn)
        controls.addWidget(test_btn)
        controls.addWidget(self.msg, 1)
        layout.addLayout(controls)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Tip: click Save .env, then restart AlphaForge to load new values."
            f"\nConfig root: {get_config_root()}"
            f"\n.env path: {get_env_path()}"
        )
        layout.addWidget(text)

    def _with_inline_error(self, field: QWidget, error: QLabel) -> QWidget:
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(2)
        wrapper_layout.addWidget(field)
        wrapper_layout.addWidget(error)
        return wrapper

    def _clear_errors(self) -> None:
        self.base_url_error.setText("")
        self.primary_model_error.setText("")
        self.fallback_model_error.setText("")
        self.db_path_error.setText("")

    def _validate(self) -> bool:
        self._clear_errors()
        valid = True

        url_text = self.base_url.text().strip()
        if not url_text:
            self.base_url_error.setText("Base URL is required.")
            valid = False
        else:
            parsed = urllib.parse.urlparse(url_text)
            if parsed.scheme not in {"http", "https"}:
                self.base_url_error.setText("Base URL must start with http:// or https://.")
                valid = False
            elif not parsed.netloc:
                self.base_url_error.setText("Base URL must include a hostname and optional port.")
                valid = False

        primary = self.primary_model.text().strip()
        if not primary:
            self.primary_model_error.setText("Primary model is required.")
            valid = False
        elif not MODEL_NAME_PATTERN.fullmatch(primary):
            self.primary_model_error.setText(
                "Primary model contains invalid characters. Use letters, numbers, ., _, :, /, -."
            )
            valid = False

        fallback = self.fallback_model.text().strip()
        if fallback and not MODEL_NAME_PATTERN.fullmatch(fallback):
            self.fallback_model_error.setText(
                "Fallback model contains invalid characters. Use letters, numbers, ., _, :, /, -."
            )
            valid = False

        db_input = self.db_path.text().strip()
        if not db_input:
            self.db_path_error.setText("DB path is required.")
            valid = False
        else:
            db_candidate = Path(db_input).expanduser()
            db_resolved = db_candidate if db_candidate.is_absolute() else (get_config_root() / db_candidate)
            if db_resolved.exists() and db_resolved.is_dir():
                self.db_path_error.setText("DB path must be a file path, not a directory.")
                valid = False

        return valid

    def _collect_values(self) -> dict[str, str]:
        return {
            "OLLAMA_BASE_URL": self.base_url.text().strip(),
            "OLLAMA_PRIMARY_MODEL": self.primary_model.text().strip(),
            "OLLAMA_FALLBACK_MODEL": self.fallback_model.text().strip(),
            "OLLAMA_TIMEOUT_SECONDS": str(int(self.timeout.value())),
            "ALPHAFORGE_DB_PATH": self.db_path.text().strip(),
        }

    def save_env(self) -> None:
        if not self._validate():
            self.msg.setText("Fix validation errors before saving.")
            return

        values = self._collect_values()
        env_path = get_env_path()
        env_path.write_text("\n".join([f"{k}={v}" for k, v in values.items()]) + "\n", encoding="utf-8")
        self.msg.setText(f"Saved {env_path}. Restart AlphaForge to apply changes.")

    def test_connection(self) -> None:
        if not self._validate():
            self.msg.setText("Fix validation errors before testing connection.")
            return

        values = self._collect_values()
        base_url = values["OLLAMA_BASE_URL"].rstrip("/")
        primary_model = values["OLLAMA_PRIMARY_MODEL"]
        fallback_model = values["OLLAMA_FALLBACK_MODEL"]
        required_models = {primary_model}
        if fallback_model:
            required_models.add(fallback_model)

        request = urllib.request.Request(url=f"{base_url}/api/tags", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=int(self.timeout.value())) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            self.msg.setText(f"Connection test failed: Ollama returned HTTP {exc.code}.")
            return
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            self.msg.setText(f"Connection test failed: could not reach {base_url}. ({exc})")
            return

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self.msg.setText("Connection test failed: Ollama returned invalid JSON from /api/tags.")
            return

        models = {
            item.get("name", "")
            for item in payload.get("models", [])
            if isinstance(item, dict) and isinstance(item.get("name", ""), str)
        }
        missing = sorted(model for model in required_models if model not in models)
        if missing:
            self.msg.setText(
                "Connection test failed: Ollama reachable, but missing model(s): " + ", ".join(missing)
            )
            return

        checked = ", ".join(sorted(required_models))
        self.msg.setText(f"Connection test passed: Ollama reachable and model(s) available: {checked}.")
