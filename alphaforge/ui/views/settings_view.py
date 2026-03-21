from __future__ import annotations

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
