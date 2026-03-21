from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from alphaforge.ai.ai_service import AIService
from alphaforge.services.analysis_service import AnalysisService
from alphaforge.ui.ai_worker import AsyncRunner


class DashboardView(QWidget):
    def __init__(self, analysis_service: AnalysisService, ai_service: AIService, parent=None):
        super().__init__(parent)
        self._analysis_service = analysis_service
        self._ai_service = ai_service
        self._runner = AsyncRunner()
        self._latest_context: dict = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Dashboard</h2>"))

        form = QFormLayout()
        self.symbol = QLineEdit("AAPL")
        self.start = QDateEdit(QDate(2024, 1, 1))
        self.end = QDateEdit(QDate.currentDate())
        self.start.setCalendarPopup(True)
        self.end.setCalendarPopup(True)
        form.addRow("Symbol", self.symbol)
        form.addRow("Start", self.start)
        form.addRow("End", self.end)
        layout.addLayout(form)

        controls = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Snapshot")
        self.refresh_btn.clicked.connect(self.refresh)
        self.ai_btn = QPushButton("AI Snapshot Insight")
        self.ai_btn.clicked.connect(self.generate_ai_insight)
        self.msg = QLabel("Ready")
        controls.addWidget(self.refresh_btn)
        controls.addWidget(self.ai_btn)
        controls.addWidget(self.msg, 1)
        layout.addLayout(controls)

        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setPlaceholderText("Snapshot metrics appear here.")
        layout.addWidget(self.summary)

        self.ai_out = QTextEdit()
        self.ai_out.setReadOnly(True)
        self.ai_out.setPlaceholderText("AI interpretation appears here.")
        layout.addWidget(self.ai_out)

    def refresh(self) -> None:
        symbol = self.symbol.text().strip().upper()
        start = self.start.date().toPython()
        end = self.end.date().toPython()
        if not symbol or not isinstance(start, date) or not isinstance(end, date) or start >= end:
            self.msg.setText("Invalid input")
            return

        frame = self._analysis_service.run(symbol, start, end).frame
        if frame.empty:
            self.msg.setText("No data")
            self.summary.setPlainText("")
            return

        last = frame.iloc[-1]
        total_return_pct = float((frame["Close"].iloc[-1] / frame["Close"].iloc[0] - 1.0) * 100)
        latest_regime = str(last.get("regime", "unknown"))
        latest_rsi = float(last.get("rsi", 0.0))
        latest_vol = float(last.get("volatility", 0.0)) * 100
        self._latest_context = {
            "symbol": symbol,
            "rows_analyzed": len(frame),
            "latest": {
                "close": float(last.get("Close", 0.0)),
                "rsi": latest_rsi,
                "volatility_pct": latest_vol,
                "regime": latest_regime,
            },
            "period_return_pct": total_return_pct,
        }
        self.summary.setPlainText(
            f"Symbol: {symbol}\n"
            f"Rows analyzed: {len(frame)}\n"
            f"Latest close: {float(last.get('Close', 0.0)):.2f}\n"
            f"Period return: {total_return_pct:.2f}%\n"
            f"Latest RSI: {latest_rsi:.2f}\n"
            f"Latest annualized vol proxy: {latest_vol:.2f}%\n"
            f"Latest regime: {latest_regime}"
        )
        self.msg.setText("Snapshot updated")

    def generate_ai_insight(self) -> None:
        if not self._latest_context:
            self.msg.setText("Refresh snapshot first")
            return

        self.ai_btn.setEnabled(False)
        self.msg.setText("Generating AI insight...")
        self._runner.run(
            self._ai_service.generate_market_insight,
            self._on_ai_done,
            self._on_ai_error,
            self._latest_context,
        )

    def _on_ai_done(self, text: str) -> None:
        self.ai_out.setPlainText(text)
        self.ai_btn.setEnabled(True)
        self.msg.setText("AI insight ready")

    def _on_ai_error(self, error: str) -> None:
        self.ai_out.setPlainText(f"AI error: {error}")
        self.ai_btn.setEnabled(True)
        self.msg.setText("AI unavailable")
