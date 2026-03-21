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
from alphaforge.ui.views.ai_chat_panel import AIChatPanel


class PortfolioView(QWidget):
    def __init__(self, analysis_service: AnalysisService, ai_service: AIService, parent=None):
        super().__init__(parent)
        self._analysis = analysis_service
        self._ai = ai_service
        self._runner = AsyncRunner()
        self._latest_context: dict = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.sym = QLineEdit("AAPL")
        self.st = QDateEdit(QDate(2024, 1, 1))
        self.en = QDateEdit(QDate.currentDate())
        self.st.setCalendarPopup(True)
        self.en.setCalendarPopup(True)
        form.addRow("Proxy Symbol", self.sym)
        form.addRow("Start", self.st)
        form.addRow("End", self.en)
        layout.addLayout(form)

        controls = QHBoxLayout()
        self.compute_btn = QPushButton("Compute Risk")
        self.compute_btn.clicked.connect(self.compute)
        self.ai_btn = QPushButton("Analyze Risk with AI")
        self.ai_btn.clicked.connect(self.analyze_ai)
        self.msg = QLabel("Ready")
        controls.addWidget(self.compute_btn)
        controls.addWidget(self.ai_btn)
        controls.addWidget(self.msg, 1)
        layout.addLayout(controls)

        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        layout.addWidget(self.summary)

        self.ai_out = QTextEdit()
        self.ai_out.setReadOnly(True)
        self.ai_out.setPlaceholderText("AI portfolio-risk interpretation will appear here.")
        layout.addWidget(self.ai_out)
        layout.addWidget(AIChatPanel(self._ai, self._get_context))

    def compute(self) -> None:
        s = self.sym.text().strip().upper()
        st = self.st.date().toPython()
        en = self.en.date().toPython()
        if not s or not isinstance(st, date) or not isinstance(en, date) or st >= en:
            self.msg.setText("Invalid input")
            return

        frame = self._analysis.run(s, st, en).frame
        if frame.empty:
            self.msg.setText("No data")
            return

        returns = frame["return"]
        daily_vol = float(returns.std()) if len(returns) > 1 else 0.0
        ann_vol_pct = daily_vol * (252**0.5) * 100
        var95_pct = float(returns.quantile(0.05) * 100)
        max_dd_pct = float((frame["Close"] / frame["Close"].cummax() - 1.0).min() * 100)
        latest = frame.iloc[-1]
        self._latest_context = {
            "symbol": s,
            "rows": int(len(frame)),
            "risk_metrics": {
                "annualized_volatility_pct": ann_vol_pct,
                "value_at_risk_95_pct": var95_pct,
                "max_drawdown_pct": max_dd_pct,
                "latest_regime": str(latest.get("regime", "")),
                "latest_rsi": float(latest.get("rsi", 0.0)),
            },
        }
        self.summary.setPlainText(
            f"Annualized Volatility: {ann_vol_pct:.2f}%\n"
            f"VaR 95% (daily): {var95_pct:.2f}%\n"
            f"Max Drawdown: {max_dd_pct:.2f}%\n"
            f"Latest Regime: {latest.get('regime', '')}\n"
            f"Latest RSI: {latest.get('rsi', 0.0):.2f}"
        )
        self.msg.setText("Risk computed")

    def analyze_ai(self) -> None:
        if not self._latest_context:
            self.msg.setText("Compute risk first")
            return

        self.ai_btn.setEnabled(False)
        self.msg.setText("Generating AI risk analysis...")
        self._runner.run(
            self._ai.analyze_portfolio,
            self._on_ai_done,
            self._on_ai_error,
            self._latest_context,
        )

    def _on_ai_done(self, text: str) -> None:
        self.ai_out.setPlainText(text)
        self.ai_btn.setEnabled(True)
        self.msg.setText("AI risk analysis ready")

    def _on_ai_error(self, error: str) -> None:
        self.ai_out.setPlainText(f"AI error: {error}")
        self.ai_btn.setEnabled(True)
        self.msg.setText("AI unavailable")

    def _get_context(self) -> dict:
        return self._latest_context
