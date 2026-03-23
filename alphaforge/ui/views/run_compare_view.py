from __future__ import annotations

from datetime import date
import csv

import pandas as pd
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFileDialog,
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

from alphaforge.services.data_service import DataService
from alphaforge.services.demo_defaults import get_demo_defaults
from alphaforge.services.view_helpers import (
    correlation_summary,
    format_service_error,
    has_valid_date_range,
    parse_symbol_list,
    run_compare_metrics,
)
from alphaforge.ui.ai_worker import AsyncRunner


CompareResult = dict[str, object]


class RunCompareView(QWidget):
    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self._data_service = data_service
        self._runner = AsyncRunner()
        self._is_comparing = False
        self._latest_rows: list[tuple[str, int, float, float, float, float, float]] = []
        self._latest_missing_symbols: list[str] = []
        self._latest_corr_summary: dict[str, object] = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        defaults = get_demo_defaults()
        self.symbols = QLineEdit(defaults.compare_symbols_text)
        self.start = QDateEdit(QDate(defaults.start_date.year, defaults.start_date.month, defaults.start_date.day))
        self.end = QDateEdit(QDate(defaults.end_date.year, defaults.end_date.month, defaults.end_date.day))
        self.start.setCalendarPopup(True)
        self.end.setCalendarPopup(True)
        form.addRow("Symbols", self.symbols)
        form.addRow("Start", self.start)
        form.addRow("End", self.end)
        layout.addLayout(form)

        controls = QHBoxLayout()
        self.btn = QPushButton("Compare")
        self.btn.clicked.connect(self.compare)
        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_csv)
        self.msg = QLabel("Ready")
        controls.addWidget(self.btn)
        controls.addWidget(self.export_btn)
        controls.addWidget(self.msg, 1)
        layout.addLayout(controls)

        corr_controls = QHBoxLayout()
        self.show_corr = QCheckBox("Show correlation summary")
        self.show_corr.setChecked(False)
        self.show_corr.toggled.connect(self._toggle_corr_summary)
        corr_controls.addWidget(self.show_corr)
        corr_controls.addStretch(1)
        layout.addLayout(corr_controls)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Symbol",
                "Rows",
                "Total Return %",
                "Annualized Return %",
                "Annualized Vol %",
                "Sharpe",
                "Max Drawdown %",
            ]
        )
        layout.addWidget(self.table)

        self.corr_summary = QTextEdit()
        self.corr_summary.setReadOnly(True)
        self.corr_summary.setVisible(False)
        self.corr_summary.setPlaceholderText("Enable correlation summary to view pairwise return relationships.")
        layout.addWidget(self.corr_summary)

    def _toggle_corr_summary(self, enabled: bool) -> None:
        self.corr_summary.setVisible(enabled)
        if enabled and self._latest_corr_summary:
            self.corr_summary.setPlainText(self._format_corr_summary(self._latest_corr_summary))

    def _friendly_error(self, error: str) -> str:
        return format_service_error(
            error,
            network_message="Network error during comparison. Check your connection and try again.",
            provider_message="Market data provider unavailable. Please retry shortly.",
            fallback_prefix="Compare failed",
        )

    def compare(self) -> None:
        if self._is_comparing:
            return
        start = self.start.date().toPython()
        end = self.end.date().toPython()
        if not has_valid_date_range(start, end):
            self.msg.setText("Invalid input.")
            return

        symbols = parse_symbol_list(self.symbols.text())
        if not symbols:
            self.msg.setText("Invalid input.")
            return

        self._is_comparing = True
        self.btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.msg.setText("Running comparison...")
        self._runner.run(self._run_compare, self._on_compare_done, self._on_compare_error, symbols, start, end)

    def _run_compare(self, symbols: list[str], start: date, end: date) -> CompareResult:
        rows: list[tuple[str, int, float, float, float, float, float]] = []
        missing: list[str] = []
        returns_map: dict[str, pd.Series] = {}
        for symbol in symbols:
            try:
                frame = self._data_service.fetch(symbol, start, end).frame
            except Exception:
                missing.append(symbol)
                continue
            if frame.empty or len(frame) < 2:
                missing.append(symbol)
                continue

            ordered = frame.sort_values("Date").reset_index(drop=True)
            total_ret, ann_ret, ann_vol, sharpe, max_drawdown = run_compare_metrics(ordered)
            rows.append((symbol, len(ordered), total_ret, ann_ret, ann_vol, sharpe, max_drawdown))
            returns_map[symbol] = ordered["Close"].pct_change()

        rows.sort(key=lambda x: x[2], reverse=True)
        corr_data: dict[str, object] = {}
        returns_df = pd.DataFrame(returns_map).dropna()
        if len(returns_df.columns) >= 2 and not returns_df.empty:
            corr = returns_df.corr()
            corr_data = correlation_summary(corr)
            corr_data["symbol_count"] = len(returns_df.columns)

        return {
            "rows": rows,
            "missing": missing,
            "correlation": corr_data,
        }

    def _on_compare_done(self, result: CompareResult) -> None:
        self._is_comparing = False
        rows = list(result.get("rows", []))
        missing = [str(item) for item in result.get("missing", [])]
        corr_summary = dict(result.get("correlation", {}))
        self._latest_rows = rows
        self._latest_missing_symbols = missing
        self._latest_corr_summary = corr_summary
        self.table.setRowCount(len(rows))
        for i, (symbol, nrows, total_ret, ann_ret, ann_vol, sharpe, max_drawdown) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(symbol))
            self.table.setItem(i, 1, QTableWidgetItem(str(nrows)))
            self.table.setItem(i, 2, QTableWidgetItem(f"{total_ret:.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{ann_ret:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{ann_vol:.2f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{sharpe:.3f}"))
            self.table.setItem(i, 6, QTableWidgetItem(f"{max_drawdown:.2f}"))

        if corr_summary:
            self.corr_summary.setPlainText(self._format_corr_summary(corr_summary))
        else:
            self.corr_summary.setPlainText("Not enough overlapping symbols with data to compute correlation summary.")

        self.btn.setEnabled(True)
        self.export_btn.setEnabled(bool(rows))
        if missing:
            preview = ", ".join(missing[:4])
            suffix = "..." if len(missing) > 4 else ""
            self.msg.setText(f"Compared {len(rows)} symbols ({len(missing)} skipped: {preview}{suffix})")
        else:
            self.msg.setText(f"Compared {len(rows)} symbols")

    def _on_compare_error(self, error: str) -> None:
        self._is_comparing = False
        self.btn.setEnabled(True)
        self.export_btn.setEnabled(bool(self._latest_rows))
        self.msg.setText(self._friendly_error(error))

    @staticmethod
    def _format_corr_summary(summary: dict[str, object]) -> str:
        return (
            f"Symbols in correlation: {int(summary.get('symbol_count', 0))}\n"
            f"Avg Pairwise Correlation: {float(summary.get('average_pairwise_corr', 0.0)):.3f}\n"
            f"Most Correlated Pair: {summary.get('top_pair', 'N/A')} "
            f"({float(summary.get('top_pair_corr', 0.0)):.3f})"
        )

    def export_csv(self) -> None:
        if not self._latest_rows:
            self.msg.setText("Run compare first")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Comparison CSV", "compare_results.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "Symbol",
                    "Rows",
                    "Total Return %",
                    "Annualized Return %",
                    "Annualized Vol %",
                    "Sharpe",
                    "Max Drawdown %",
                ]
            )
            for symbol, nrows, total_ret, ann_ret, ann_vol, sharpe, max_drawdown in self._latest_rows:
                writer.writerow([symbol, nrows, f"{total_ret:.6f}", f"{ann_ret:.6f}", f"{ann_vol:.6f}", f"{sharpe:.6f}", f"{max_drawdown:.6f}"])

            if self._latest_missing_symbols:
                writer.writerow([])
                writer.writerow(["Skipped Symbols"])
                for symbol in self._latest_missing_symbols:
                    writer.writerow([symbol])

            if self._latest_corr_summary:
                writer.writerow([])
                writer.writerow(["Correlation Summary"])
                writer.writerow(["Symbols in correlation", self._latest_corr_summary.get("symbol_count", 0)])
                writer.writerow(["Avg Pairwise Correlation", f"{float(self._latest_corr_summary.get('average_pairwise_corr', 0.0)):.6f}"])
                writer.writerow(["Most Correlated Pair", self._latest_corr_summary.get("top_pair", "N/A")])
                writer.writerow(["Most Correlated Pair Corr", f"{float(self._latest_corr_summary.get('top_pair_corr', 0.0)):.6f}"])
        self.msg.setText(f"Exported CSV to {path}")
