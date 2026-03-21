from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDoubleSpinBox,
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
from alphaforge.services.backtest_service import BacktestService
from alphaforge.ui.ai_worker import AsyncRunner
from alphaforge.ui.views.ai_chat_panel import AIChatPanel


class BacktestView(QWidget):
    def __init__(self, backtest_service: BacktestService, ai_service: AIService, parent=None):
        super().__init__(parent)
        self._s = backtest_service
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
        self.c = QDoubleSpinBox()
        self.c.setRange(0, 200)
        self.c.setValue(5)
        self.c.setSuffix(" bps")
        self.sl = QDoubleSpinBox()
        self.sl.setRange(0, 200)
        self.sl.setValue(3)
        self.sl.setSuffix(" bps")
        f.addRow("Symbol", self.sym)
        f.addRow("Start", self.st)
        f.addRow("End", self.en)
        f.addRow("Commission", self.c)
        f.addRow("Slippage", self.sl)
        l.addLayout(f)

        a = QHBoxLayout()
        self.btn = QPushButton("Run MA Backtest")
        self.btn.clicked.connect(self.run)
        self.ai_btn = QPushButton("Explain this strategy result")
        self.ai_btn.clicked.connect(self.generate_ai_explanation)
        self.msg = QLabel("Ready")
        a.addWidget(self.btn)
        a.addWidget(self.ai_btn)
        a.addWidget(self.msg, 1)
        l.addLayout(a)

        self.out = QTextEdit()
        self.out.setReadOnly(True)
        l.addWidget(self.out)

        self.ai_out = QTextEdit()
        self.ai_out.setReadOnly(True)
        self.ai_out.setPlaceholderText("AI strategy explanation will appear here.")
        l.addWidget(self.ai_out)
        l.addWidget(AIChatPanel(self._ai, self._get_context))

    def run(self):
        s = self.sym.text().strip().upper()
        st = self.st.date().toPython()
        en = self.en.date().toPython()
        if not s or not isinstance(st, date) or not isinstance(en, date) or st >= en:
            self.msg.setText("Invalid input")
            return

        r = self._s.run_ma(s, st, en, float(self.c.value()), float(self.sl.value()))
        self._latest_context = {
            "symbol": s,
            "commission_bps": float(self.c.value()),
            "slippage_bps": float(self.sl.value()),
            "metrics": {
                "trend_bias": "long_only_ma_crossover",
                "total_return_pct": r.total_return_pct,
                "annualized_return_pct": r.annualized_return_pct,
                "annualized_vol_pct": r.annualized_vol_pct,
                "sharpe": r.sharpe,
                "max_drawdown_pct": r.max_drawdown_pct,
            },
        }
        self.out.setPlainText(
            f"Total Return: {r.total_return_pct:.2f}%\n"
            f"Annualized Return: {r.annualized_return_pct:.2f}%\n"
            f"Annualized Volatility: {r.annualized_vol_pct:.2f}%\n"
            f"Sharpe: {r.sharpe:.3f}\n"
            f"Max Drawdown: {r.max_drawdown_pct:.2f}%"
        )
        self.msg.setText("Backtest complete")

    def generate_ai_explanation(self) -> None:
        if not self._latest_context:
            self.msg.setText("Run backtest first")
            return

        self.ai_btn.setEnabled(False)
        self.msg.setText("Generating AI explanation...")
        self._runner.run(
            self._ai.explain_strategy,
            self._on_ai_done,
            self._on_ai_error,
            self._latest_context,
        )

    def _on_ai_done(self, text: str) -> None:
        self.ai_out.setPlainText(text)
        self.ai_btn.setEnabled(True)
        self.msg.setText("AI explanation ready")

    def _on_ai_error(self, error: str) -> None:
        self.ai_out.setPlainText(f"AI error: {error}")
        self.ai_btn.setEnabled(True)
        self.msg.setText("AI unavailable")

    def _get_context(self) -> dict:
        return self._latest_context
