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
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from alphaforge.ai.ai_service import AIService
from alphaforge.services.analysis_service import AnalysisService
from alphaforge.ui.ai_worker import AsyncRunner
from alphaforge.ui.views.ai_chat_panel import AIChatPanel


class IndicatorsRegimeView(QWidget):
    def __init__(self, analysis_service: AnalysisService, ai_service: AIService, parent=None):
        super().__init__(parent)
        self._s = analysis_service
        self._ai = ai_service
        self._runner = AsyncRunner()
        self._latest_context: dict = {}
        self._build()

    def _build(self):
        l = QVBoxLayout(self)
        f = QFormLayout()
        self.sym = QLineEdit("AAPL")
        self.st = QDateEdit(QDate(2024, 1, 1))
        self.en = QDateEdit(QDate.currentDate())
        self.st.setCalendarPopup(True)
        self.en.setCalendarPopup(True)
        f.addRow("Symbol", self.sym)
        f.addRow("Start", self.st)
        f.addRow("End", self.en)
        l.addLayout(f)

        a = QHBoxLayout()
        self.btn = QPushButton("Compute")
        self.btn.clicked.connect(self.run)
        self.ai_btn = QPushButton("AI Insight")
        self.ai_btn.clicked.connect(self.generate_ai_insight)
        self.msg = QLabel("Ready")
        a.addWidget(self.btn)
        a.addWidget(self.ai_btn)
        a.addWidget(self.msg, 1)
        l.addLayout(a)

        self.t = QTableWidget(0, 6)
        self.t.setHorizontalHeaderLabels(["Date", "Close", "MA Fast", "MA Slow", "RSI", "Regime"])
        l.addWidget(self.t)

        self.ai_out = QTextEdit()
        self.ai_out.setReadOnly(True)
        self.ai_out.setPlaceholderText("AI market interpretation will appear here.")
        l.addWidget(self.ai_out)
        l.addWidget(AIChatPanel(self._ai, self._get_context))

    def run(self):
        s = self.sym.text().strip().upper()
        st = self.st.date().toPython()
        en = self.en.date().toPython()
        if not s or not isinstance(st, date) or not isinstance(en, date) or st >= en:
            self.msg.setText("Invalid input")
            return

        r = self._s.run(s, st, en).frame
        tail = r.tail(120).reset_index(drop=True)
        self.t.setRowCount(len(tail))
        for i, (_, x) in enumerate(tail.iterrows()):
            self.t.setItem(i, 0, QTableWidgetItem(str(x.get("Date", ""))))
            self.t.setItem(i, 1, QTableWidgetItem(f"{x.get('Close', 0):.2f}"))
            self.t.setItem(i, 2, QTableWidgetItem(f"{x.get('ma_fast', 0):.2f}"))
            self.t.setItem(i, 3, QTableWidgetItem(f"{x.get('ma_slow', 0):.2f}"))
            self.t.setItem(i, 4, QTableWidgetItem(f"{x.get('rsi', 0):.2f}"))
            self.t.setItem(i, 5, QTableWidgetItem(str(x.get("regime", ""))))

        last = r.iloc[-1] if len(r) else {}
        self._latest_context = {
            "symbol": s,
            "rows": int(len(r)),
            "latest": {
                "trend": "uptrend" if float(last.get("ma_fast", 0.0)) >= float(last.get("ma_slow", 0.0)) else "downtrend",
                "close": float(last.get("Close", 0.0)) if len(r) else 0.0,
                "ma_fast": float(last.get("ma_fast", 0.0)) if len(r) else 0.0,
                "ma_slow": float(last.get("ma_slow", 0.0)) if len(r) else 0.0,
                "rsi": float(last.get("rsi", 0.0)) if len(r) else 0.0,
                "volatility": float(last.get("volatility", 0.0)) if len(r) else 0.0,
                "regime": str(last.get("regime", "")) if len(r) else "",
            },
            "returns_5d_pct": float(r["return"].tail(5).sum() * 100) if len(r) else 0.0,
        }
        self.msg.setText(f"Computed {len(tail)} rows")

    def generate_ai_insight(self) -> None:
        if not self._latest_context:
            self.msg.setText("Compute indicators first")
            return

        self.ai_btn.setEnabled(False)
        self.msg.setText("Generating AI insight...")
        self._runner.run(
            self._ai.generate_market_insight,
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

    def _get_context(self) -> dict:
        return self._latest_context
