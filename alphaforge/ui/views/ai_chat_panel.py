from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from alphaforge.ai.ai_service import AIService
from alphaforge.ui.ai_worker import AsyncRunner


class AIChatPanel(QWidget):
    def __init__(self, ai_service: AIService, context_provider: Callable[[], dict], parent=None):
        super().__init__(parent)
        self._ai_service = ai_service
        self._context_provider = context_provider
        self._runner = AsyncRunner()
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("AI Copilot Chat"))

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Ask: Why is this risky? Explain this strategy.")
        layout.addWidget(self.output)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type question...")
        self.input.returnPressed.connect(self.send)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send)
        row.addWidget(self.input, 1)
        row.addWidget(self.send_btn)
        layout.addLayout(row)

        self.status = QLabel("Ready")
        layout.addWidget(self.status)

    def send(self) -> None:
        question = self.input.text().strip()
        if not question:
            self.status.setText("Ask a question first.")
            return

        context = self._context_provider()
        self.send_btn.setEnabled(False)
        self.status.setText("Asking local Ollama...")
        self.output.append(f"\nYou: {question}\n")
        self._runner.run(
            self._ai_service.chat,
            self._on_answer,
            self._on_error,
            question,
            context,
        )

    def _on_answer(self, answer: str) -> None:
        self.output.append(f"Copilot: {answer}\n")
        self.input.clear()
        self.send_btn.setEnabled(True)
        self.status.setText("Ready")

    def _on_error(self, error_text: str) -> None:
        self.output.append(f"Copilot error: {error_text}\n")
        self.send_btn.setEnabled(True)
        self.status.setText("AI unavailable. Check Ollama and retry.")
