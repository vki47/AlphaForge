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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from alphaforge.services.data_service import DataService
from alphaforge.services.view_helpers import (
    format_service_error,
    has_valid_date_range,
    parse_symbol_list,
    run_compare_metrics,
)
from alphaforge.ui.ai_worker import AsyncRunner


class RunCompareView(QWidget):
    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self._data_service = data_service
        self._runner = AsyncRunner()
        self._is_comparing = False
        self._latest_rows: list[tuple[str, int, float, float, float, float, float]] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.symbols = QLineEdit("AAPL,MSFT,NVDA")
        self.start = QDateEdit(QDate(2024, 1, 1))
        self.end = QDateEdit(QDate.currentDate())
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

    def _run_compare(self, symbols: list[str], start: date, end: date) -> list[tuple[str, int, float, float, float, float, float]]:
        rows: list[tuple[str, int, float, float, float, float, float]] = []
        for symbol in symbols:
            frame = self._data_service.fetch(symbol, start, end).frame
            if frame.empty or len(frame) < 2:
                continue

            ordered = frame.sort_values("Date").reset_index(drop=True)
            total_ret, ann_ret, ann_vol, sharpe, max_drawdown = run_compare_metrics(ordered)
            rows.append((symbol, len(ordered), total_ret, ann_ret, ann_vol, sharpe, max_drawdown))

        rows.sort(key=lambda x: x[2], reverse=True)
        return rows

    def _on_compare_done(self, rows: list[tuple[str, int, float, float, float, float, float]]) -> None:
        self._is_comparing = False
        self._latest_rows = rows
        self.table.setRowCount(len(rows))
        for i, (symbol, nrows, total_ret, ann_ret, ann_vol, sharpe, max_drawdown) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(symbol))
            self.table.setItem(i, 1, QTableWidgetItem(str(nrows)))
            self.table.setItem(i, 2, QTableWidgetItem(f"{total_ret:.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{ann_ret:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{ann_vol:.2f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{sharpe:.3f}"))
            self.table.setItem(i, 6, QTableWidgetItem(f"{max_drawdown:.2f}"))

        self.btn.setEnabled(True)
        self.export_btn.setEnabled(bool(rows))
        self.msg.setText(f"Compared {len(rows)} symbols")

    def _on_compare_error(self, error: str) -> None:
        self._is_comparing = False
        self.btn.setEnabled(True)
        self.export_btn.setEnabled(bool(self._latest_rows))
        self.msg.setText(self._friendly_error(error))

    def export_csv(self) -> None:
        if not self._latest_rows:
            self.msg.setText("Run compare first")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Comparison CSV", "compare_results.csv", "CSV (*.csv)")
        if not path:
            return
        lines = [
            "Symbol,Rows,Total Return %,Annualized Return %,Annualized Vol %,Sharpe,Max Drawdown %",
        ]
        for symbol, nrows, total_ret, ann_ret, ann_vol, sharpe, max_drawdown in self._latest_rows:
            lines.append(
                f"{symbol},{nrows},{total_ret:.6f},{ann_ret:.6f},{ann_vol:.6f},{sharpe:.6f},{max_drawdown:.6f}"
            )
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        self.msg.setText(f"Exported CSV to {path}")
