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
    QVBoxLayout,
    QWidget,
)

from alphaforge.services.data_service import DataService
from alphaforge.services.view_helpers import run_compare_metrics


class RunCompareView(QWidget):
    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self._data_service = data_service
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
        self.msg = QLabel("Ready")
        controls.addWidget(self.btn)
        controls.addWidget(self.msg, 1)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Symbol", "Rows", "Total Return %", "Annualized Return %", "Annualized Vol %"]
        )
        layout.addWidget(self.table)

    def compare(self) -> None:
        start = self.start.date().toPython()
        end = self.end.date().toPython()
        if not isinstance(start, date) or not isinstance(end, date) or start >= end:
            self.msg.setText("Invalid date input")
            return

        symbols = [s.strip().upper() for s in self.symbols.text().split(",") if s.strip()]
        if not symbols:
            self.msg.setText("Provide at least one symbol")
            return

        rows: list[tuple[str, int, float, float, float]] = []
        for symbol in symbols:
            frame = self._data_service.fetch(symbol, start, end).frame
            if frame.empty or len(frame) < 2:
                continue

            ordered = frame.sort_values("Date").reset_index(drop=True)
            total_ret, ann_ret, ann_vol = self._calculate_metrics(ordered)
            rows.append((symbol, len(ordered), total_ret, ann_ret, ann_vol))

        rows.sort(key=lambda x: x[2], reverse=True)
        self.table.setRowCount(len(rows))
        for i, (symbol, nrows, total_ret, ann_ret, ann_vol) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(symbol))
            self.table.setItem(i, 1, QTableWidgetItem(str(nrows)))
            self.table.setItem(i, 2, QTableWidgetItem(f"{total_ret:.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{ann_ret:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{ann_vol:.2f}"))

        self.msg.setText(f"Compared {len(rows)} symbols")

    @staticmethod
    def _calculate_metrics(frame) -> tuple[float, float, float]:
        return run_compare_metrics(frame)
