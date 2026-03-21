from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDoubleSpinBox,
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
from alphaforge.services.view_helpers import build_research_report_markdown
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
        self._is_generating = False
        self._latest_context: dict = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.symbol = QLineEdit("AAPL")
        self.start = QDateEdit(QDate(2024, 1, 1))
        self.end = QDateEdit(QDate.currentDate())
        self.commission = QDoubleSpinBox()
        self.commission.setRange(0.0, 200.0)
        self.commission.setValue(5.0)
        self.commission.setSuffix(" bps")
        self.slippage = QDoubleSpinBox()
        self.slippage.setRange(0.0, 200.0)
        self.slippage.setValue(3.0)
        self.slippage.setSuffix(" bps")
        self.compare_symbol = QLineEdit("")
        self.compare_symbol.setPlaceholderText("Optional symbol, e.g. MSFT")
        self.start.setCalendarPopup(True)
        self.end.setCalendarPopup(True)
        form.addRow("Symbol", self.symbol)
        form.addRow("Start", self.start)
        form.addRow("End", self.end)
        form.addRow("Commission", self.commission)
        form.addRow("Slippage", self.slippage)
        form.addRow("Compare Symbol (Optional)", self.compare_symbol)
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
        if self._is_generating:
            return
        symbol = self.symbol.text().strip().upper()
        start = self.start.date().toPython()
        end = self.end.date().toPython()
        if not symbol or not isinstance(start, date) or not isinstance(end, date) or start >= end:
            self.msg.setText("Invalid input")
            return

        self._is_generating = True
        self.btn.setEnabled(False)
        self.ai_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.msg.setText("Generating report...")
        self._runner.run(
            self._build_report,
            self._on_generate_done,
            self._on_generate_error,
            symbol,
            start,
            end,
            float(self.commission.value()),
            float(self.slippage.value()),
            self.compare_symbol.text().strip().upper(),
        )

    def _build_report(
        self,
        symbol: str,
        start: date,
        end: date,
        commission_bps: float,
        slippage_bps: float,
        compare_symbol: str,
    ) -> tuple[str, dict]:
        analysis = self._analysis_service.run(symbol, start, end).frame
        if analysis.empty:
            return "", {}

        backtest = self._backtest_service.run_ma(
            symbol,
            start,
            end,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
        )
        latest = analysis.iloc[-1]
        compare_snapshot = None
        if compare_symbol and compare_symbol != symbol:
            compare_analysis = self._analysis_service.run(compare_symbol, start, end).frame
            if not compare_analysis.empty and len(compare_analysis) >= 2:
                compare_latest = compare_analysis.iloc[-1]
                compare_snapshot = {
                    "symbol": compare_symbol,
                    "latest_close": float(compare_latest.get("Close", 0.0)),
                    "latest_rsi": float(compare_latest.get("rsi", 0.0)),
                    "latest_regime": str(compare_latest.get("regime", "unknown")),
                    "period_return_pct": float(
                        (compare_analysis["Close"].iloc[-1] / compare_analysis["Close"].iloc[0] - 1.0) * 100
                    ),
                }
        context = {
            "symbol": symbol,
            "rows_analyzed": len(analysis),
            "commission_bps": commission_bps,
            "slippage_bps": slippage_bps,
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
        if compare_snapshot:
            context["compare_symbol"] = compare_snapshot

        report = build_research_report_markdown(
            symbol=symbol,
            rows_analyzed=len(analysis),
            latest_close=float(latest.get("Close", 0.0)),
            latest_rsi=float(latest.get("rsi", 0.0)),
            latest_regime=str(latest.get("regime", "unknown")),
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            total_return_pct=backtest.total_return_pct,
            annualized_return_pct=backtest.annualized_return_pct,
            annualized_volatility_pct=backtest.annualized_vol_pct,
            sharpe=backtest.sharpe,
            max_drawdown_pct=backtest.max_drawdown_pct,
            compare_snapshot=compare_snapshot,
        )
        return report, context

    def _on_generate_done(self, result: tuple[str, dict]) -> None:
        self._is_generating = False
        report, context = result
        self.btn.setEnabled(True)
        self.ai_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        if not report:
            self._latest_context = {}
            self.out.clear()
            self.msg.setText("No data")
            return
        self._latest_context = context
        self.out.setPlainText(report)
        self.msg.setText("Report generated")

    def _on_generate_error(self, error: str) -> None:
        self._is_generating = False
        self.btn.setEnabled(True)
        self.ai_btn.setEnabled(bool(self._latest_context))
        self.save_btn.setEnabled(bool(self.out.toPlainText().strip()))
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
