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
from alphaforge.services.view_helpers import format_service_error, has_valid_symbol_and_date_range, normalize_symbol
from alphaforge.ui.ai_worker import AsyncRunner


class DataView(QWidget):
    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self._s = data_service
        self._runner = AsyncRunner()
        self._is_fetching = False
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.sym = QLineEdit("AAPL")
        self.st = QDateEdit(QDate(2024, 1, 1))
        self.en = QDateEdit(QDate.currentDate())
        self.st.setCalendarPopup(True)
        self.en.setCalendarPopup(True)
        form.addRow("Symbol", self.sym)
        form.addRow("Start", self.st)
        form.addRow("End", self.en)
        layout.addLayout(form)

        actions = QHBoxLayout()
        self.btn = QPushButton("Fetch Data")
        self.btn.clicked.connect(self.fetch)
        self.msg = QLabel("Ready")
        actions.addWidget(self.btn)
        actions.addWidget(self.msg, 1)
        layout.addLayout(actions)

        self.t = QTableWidget(0, 6)
        self.t.setHorizontalHeaderLabels(["Date", "Open", "High", "Low", "Close", "Volume"])
        layout.addWidget(self.t)

    def _friendly_error(self, error: str) -> str:
        return format_service_error(
            error,
            network_message="Network error while fetching data. Check your connection and try again.",
            provider_message="Data provider unavailable. Please try again in a moment.",
            fallback_prefix="Error",
        )

    def _inputs(self) -> tuple[str, date, date]:
        symbol = normalize_symbol(self.sym.text())
        start = self.st.date().toPython()
        end = self.en.date().toPython()
        return symbol, start, end

    def _set_fetch_state(self, *, is_fetching: bool) -> None:
        self._is_fetching = is_fetching
        self.btn.setEnabled(not is_fetching)

    def fetch(self) -> None:
        if self._is_fetching:
            return
        symbol, start, end = self._inputs()
        if not has_valid_symbol_and_date_range(symbol, start, end):
            self.msg.setText("Invalid input.")
            return

        self._set_fetch_state(is_fetching=True)
        self.msg.setText("Fetching data...")
        self._runner.run(self._fetch_data, self._on_fetch_done, self._on_fetch_error, symbol, start, end)

    def _fetch_data(self, symbol: str, start: date, end: date):
        return self._s.fetch(symbol, start, end)

    def _populate_table(self, frame) -> None:
        self.t.setRowCount(len(frame))
        for i, (_, row) in enumerate(frame.iterrows()):
            self.t.setItem(i, 0, QTableWidgetItem(str(row.get("Date", ""))))
            self.t.setItem(i, 1, QTableWidgetItem(f"{row.get('Open', 0):.2f}"))
            self.t.setItem(i, 2, QTableWidgetItem(f"{row.get('High', 0):.2f}"))
            self.t.setItem(i, 3, QTableWidgetItem(f"{row.get('Low', 0):.2f}"))
            self.t.setItem(i, 4, QTableWidgetItem(f"{row.get('Close', 0):.2f}"))
            self.t.setItem(i, 5, QTableWidgetItem(f"{row.get('Volume', 0):.0f}"))

    def _on_fetch_done(self, result) -> None:
        frame = result.frame
        self._populate_table(frame)
        self._set_fetch_state(is_fetching=False)
        source = getattr(result, "source", "yfinance")
        self.msg.setText(f"Loaded {len(frame)} rows from {source}")

    def _on_fetch_error(self, error: str) -> None:
        self._set_fetch_state(is_fetching=False)
        self.msg.setText(self._friendly_error(error))
