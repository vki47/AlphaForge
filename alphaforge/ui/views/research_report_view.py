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
from alphaforge.services.view_helpers import (
    build_research_report_markdown,
    format_service_error,
    has_valid_symbol_and_date_range,
    normalize_symbol,
)
from alphaforge.ui.ai_worker import AsyncRunner


class ResearchReportView(QWidget):
    _AI_SUMMARY_HEADER = "## AI Executive Summary"

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
        return format_service_error(
            error,
            network_message="Network error while generating report. Check your connection and try again.",
            provider_message="Data or AI provider unavailable. Please try again shortly.",
            fallback_prefix="Report generation failed. Please try again.",
        )

    def _set_generate_state(self, *, is_generating: bool) -> None:
        self._is_generating = is_generating
        self.btn.setEnabled(not is_generating)
        if is_generating:
            self.ai_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
        else:
            has_context = bool(self._latest_context)
            has_report = bool(self.out.toPlainText().strip())
            self.ai_btn.setEnabled(has_context)
            self.save_btn.setEnabled(has_report)

    def generate(self) -> None:
        if self._is_generating:
            return
        symbol = normalize_symbol(self.symbol.text())
        start = self.start.date().toPython()
        end = self.end.date().toPython()
        if not has_valid_symbol_and_date_range(symbol, start, end):
            self.msg.setText("Invalid input.")
            return

        self._set_generate_state(is_generating=True)
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
            normalize_symbol(self.compare_symbol.text()),
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
            context["relative_performance_pct"] = backtest.total_return_pct - float(compare_snapshot["period_return_pct"])

        report = build_research_report_markdown(
            symbol=symbol,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
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
        self._set_generate_state(is_generating=False)
        report, context = result
        if not report:
            self._latest_context = {}
            self.out.clear()
            self.ai_out.clear()
            self._set_generate_state(is_generating=False)
            self.msg.setText("No data")
            return
        self._latest_context = context
        self.out.setPlainText(report)
        self.ai_out.clear()
        self._set_generate_state(is_generating=False)
        self.msg.setText("Report generated")

    def _on_generate_error(self, error: str) -> None:
        self._set_generate_state(is_generating=False)
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
        self._merge_ai_summary_into_report(text)
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
        ai_text = self.ai_out.toPlainText().strip()
        if ai_text and not ai_text.lower().startswith("ai error:"):
            text = self._merge_ai_summary(text, ai_text)
        path, _ = QFileDialog.getSaveFileName(self, "Save Report", "research_report.md", "Markdown (*.md)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            self.msg.setText(f"Saved to {path}")
        except OSError as exc:
            self.msg.setText(f"Save failed: {exc}")

    def _merge_ai_summary_into_report(self, ai_summary: str) -> None:
        base_report = self.out.toPlainText().strip()
        if not base_report:
            return
        self.out.setPlainText(self._merge_ai_summary(base_report, ai_summary))

    def _merge_ai_summary(self, base_report: str, ai_summary: str) -> str:
        summary_block = f"{self._AI_SUMMARY_HEADER}\n\n{ai_summary.strip()}"
        marker = f"\n{self._AI_SUMMARY_HEADER}\n"
        if marker in base_report:
            return f"{base_report.split(marker, 1)[0].rstrip()}\n\n{summary_block}\n"
        return f"{base_report.rstrip()}\n\n{summary_block}\n"
