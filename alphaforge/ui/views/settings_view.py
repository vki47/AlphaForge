from __future__ import annotations

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
from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from alphaforge.utils_config import AppConfig


class SettingsView(QWidget):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Settings</h2>"))
        layout.addWidget(QLabel("Edit config and write to local `.env` (restart app to apply)."))

        form = QFormLayout()
        self.base_url = QLineEdit(self._config.ollama_base_url)
        self.primary_model = QLineEdit(self._config.ollama_primary_model)
        self.fallback_model = QLineEdit(self._config.ollama_fallback_model)
        self.timeout = QSpinBox()
        self.timeout.setRange(1, 300)
        self.timeout.setValue(int(self._config.ollama_timeout_seconds))
        self.db_path = QLineEdit(str(self._config.db_path))
        form.addRow("OLLAMA_BASE_URL", self.base_url)
        form.addRow("OLLAMA_PRIMARY_MODEL", self.primary_model)
        form.addRow("OLLAMA_FALLBACK_MODEL", self.fallback_model)
        form.addRow("OLLAMA_TIMEOUT_SECONDS", self.timeout)
        form.addRow("ALPHAFORGE_DB_PATH", self.db_path)
        layout.addLayout(form)

        controls = QHBoxLayout()
        save_btn = QPushButton("Save .env")
        save_btn.clicked.connect(self.save_env)
        self.msg = QLabel("Ready")
        controls.addWidget(save_btn)
        controls.addWidget(self.msg, 1)
        layout.addLayout(controls)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText("Tip: click Save .env, then restart AlphaForge to load new values.")
        layout.addWidget(text)

    def save_env(self) -> None:
        values = {
            "OLLAMA_BASE_URL": self.base_url.text().strip(),
            "OLLAMA_PRIMARY_MODEL": self.primary_model.text().strip(),
            "OLLAMA_FALLBACK_MODEL": self.fallback_model.text().strip(),
            "OLLAMA_TIMEOUT_SECONDS": str(int(self.timeout.value())),
            "ALPHAFORGE_DB_PATH": self.db_path.text().strip(),
        }
        if not values["OLLAMA_BASE_URL"] or not values["OLLAMA_PRIMARY_MODEL"] or not values["ALPHAFORGE_DB_PATH"]:
            self.msg.setText("Required field missing")
            return

        env_path = Path.cwd() / ".env"
        env_path.write_text("\n".join([f"{k}={v}" for k, v in values.items()]) + "\n", encoding="utf-8")
        self.msg.setText(f"Saved {env_path}")
        layout.addWidget(QLabel("Current runtime configuration (read-only):"))

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "\n".join(
                [
                    f"OLLAMA_BASE_URL={self._config.ollama_base_url}",
                    f"OLLAMA_PRIMARY_MODEL={self._config.ollama_primary_model}",
                    f"OLLAMA_FALLBACK_MODEL={self._config.ollama_fallback_model}",
                    f"OLLAMA_TIMEOUT_SECONDS={self._config.ollama_timeout_seconds}",
                    f"ALPHAFORGE_DB_PATH={self._config.db_path}",
                ]
            )
        )
        layout.addWidget(text)
