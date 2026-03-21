from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QFileDialog,
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
from alphaforge.services.backtest_service import BacktestService
from alphaforge.ui.ai_worker import AsyncRunner


class ResearchReportView(QWidget):
    def __init__(
        self,
        analysis_service: AnalysisService,
        backtest_service: BacktestService,
        ai_service: AIService,
        parent=None,
    ):
        super().__init__(parent)
        self._analysis_service = analysis_service
        self._backtest_service = backtest_service
        self._ai_service = ai_service
        self._runner = AsyncRunner()
        self._latest_context: dict = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
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
        self.btn = QPushButton("Generate Report")
        self.btn.clicked.connect(self.generate)
        self.ai_btn = QPushButton("AI Executive Summary")
        self.ai_btn.clicked.connect(self.generate_ai_summary)
        self.save_btn = QPushButton("Save Report")
        self.save_btn.clicked.connect(self.save_report)
        self.msg = QLabel("Ready")
        controls.addWidget(self.btn)
        controls.addWidget(self.ai_btn)
        controls.addWidget(self.save_btn)
        controls.addWidget(self.msg, 1)
        layout.addLayout(controls)

        self.out = QTextEdit()
        self.out.setReadOnly(True)
        self.out.setPlaceholderText("Research report output appears here.")
        layout.addWidget(self.out)

        self.ai_out = QTextEdit()
        self.ai_out.setReadOnly(True)
        self.ai_out.setPlaceholderText("AI executive summary appears here.")
        layout.addWidget(self.ai_out)

    def _friendly_error(self, error: str) -> str:
        text = (error or "").strip()
        lowered = text.lower()
        if any(token in lowered for token in ["timeout", "connection", "network", "dns", "ssl", "unreachable"]):
            return "Network error while generating report. Check your connection and try again."
        if any(token in lowered for token in ["provider", "rate limit", "forbidden", "unauthorized", "api key", "429"]):
            return "Data or AI provider unavailable. Please try again shortly."
        return f"Report error: {text or 'Unknown failure'}"

    def generate(self) -> None:
        symbol = self.symbol.text().strip().upper()
        start = self.start.date().toPython()
        end = self.end.date().toPython()
        if not symbol or not isinstance(start, date) or not isinstance(end, date) or start >= end:
            self.msg.setText("Invalid input")
            return

        self.btn.setEnabled(False)
        self.ai_btn.setEnabled(False)
        self.msg.setText("Generating report...")
        self._runner.run(self._build_report, self._on_generate_done, self._on_generate_error, symbol, start, end)

    def _build_report(self, symbol: str, start: date, end: date) -> tuple[str, dict]:
        analysis = self._analysis_service.run(symbol, start, end).frame
        if analysis.empty:
            return "", {}

        backtest = self._backtest_service.run_ma(symbol, start, end, commission_bps=5.0, slippage_bps=3.0)
        latest = analysis.iloc[-1]
        context = {
            "symbol": symbol,
            "rows_analyzed": len(analysis),
            "latest": {
                "close": float(latest.get("Close", 0.0)),
                "rsi": float(latest.get("rsi", 0.0)),
                "regime": str(latest.get("regime", "unknown")),
            },
            "backtest": {
                "total_return_pct": backtest.total_return_pct,
                "annualized_return_pct": backtest.annualized_return_pct,
                "annualized_volatility_pct": backtest.annualized_vol_pct,
                "sharpe": backtest.sharpe,
                "max_drawdown_pct": backtest.max_drawdown_pct,
            },
        }
        report = (
            f"# Research Report: {symbol}\n\n"
            f"## Market Snapshot\n"
            f"- Rows analyzed: {len(analysis)}\n"
            f"- Latest close: {float(latest.get('Close', 0.0)):.2f}\n"
            f"- Latest RSI: {float(latest.get('rsi', 0.0)):.2f}\n"
            f"- Latest regime: {str(latest.get('regime', 'unknown'))}\n\n"
            f"## MA Crossover Backtest (5 bps commission, 3 bps slippage)\n"
            f"- Total Return: {backtest.total_return_pct:.2f}%\n"
            f"- Annualized Return: {backtest.annualized_return_pct:.2f}%\n"
            f"- Annualized Volatility: {backtest.annualized_vol_pct:.2f}%\n"
            f"- Sharpe: {backtest.sharpe:.3f}\n"
            f"- Max Drawdown: {backtest.max_drawdown_pct:.2f}%\n"
        )
        return report, context

    def _on_generate_done(self, result: tuple[str, dict]) -> None:
        report, context = result
        self.btn.setEnabled(True)
        self.ai_btn.setEnabled(True)
        if not report:
            self._latest_context = {}
            self.out.clear()
            self.msg.setText("No data")
            return
        self._latest_context = context
        self.out.setPlainText(report)
        self.msg.setText("Report generated")

    def _on_generate_error(self, error: str) -> None:
        self.btn.setEnabled(True)
        self.ai_btn.setEnabled(bool(self._latest_context))
        self.msg.setText(self._friendly_error(error))

    def generate_ai_summary(self) -> None:
        if not self._latest_context:
            self.msg.setText("Generate report first")
            return
        self.ai_btn.setEnabled(False)
        self.msg.setText("Generating AI summary...")
        self._runner.run(
            self._ai_service.explain_strategy,
            self._on_ai_done,
            self._on_ai_error,
            self._latest_context,
        )

    def _on_ai_done(self, text: str) -> None:
        self.ai_out.setPlainText(text)
        self.ai_btn.setEnabled(True)
        self.msg.setText("AI summary ready")

    def _on_ai_error(self, error: str) -> None:
        self.ai_out.setPlainText(f"AI error: {error}")
        self.ai_btn.setEnabled(True)
        self.msg.setText("AI unavailable")

    def save_report(self) -> None:
        text = self.out.toPlainText().strip()
        if not text:
            self.msg.setText("Generate report first")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Report", "research_report.md", "Markdown (*.md)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        self.msg.setText(f"Saved to {path}")
