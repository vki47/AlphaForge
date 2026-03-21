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
from alphaforge.utils_config import AppConfig


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

    def save_env(self) -> None:
        values = self._env_values()
        if not self._has_required_fields(values):
            self.msg.setText("Required field missing")
            return

        env_path = self._resolve_env_path()
        self._write_env_file(env_path, values)
        self.msg.setText(f"Saved {env_path}")

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
    def _resolve_env_path(base_dir: Path | None = None) -> Path:
        return resolve_env_path(base_dir)

    @staticmethod
    def _write_env_file(env_path: Path, values: dict[str, str]) -> None:
        write_env_file(env_path, values)
