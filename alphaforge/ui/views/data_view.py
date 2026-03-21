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
from alphaforge.ui.ai_worker import AsyncRunner


class DataView(QWidget):
    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self._s = data_service
        self._runner = AsyncRunner()
        self._is_fetching = False
        self._build()

    def _build(self) -> None:
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
        self.btn = QPushButton("Fetch Data")
        self.btn.clicked.connect(self.fetch)
        self.msg = QLabel("Ready")
        a.addWidget(self.btn)
        a.addWidget(self.msg, 1)
        l.addLayout(a)

        self.t = QTableWidget(0, 6)
        self.t.setHorizontalHeaderLabels(["Date", "Open", "High", "Low", "Close", "Volume"])
        l.addWidget(self.t)

    def _friendly_error(self, error: str) -> str:
        text = (error or "").strip()
        lowered = text.lower()
        if any(token in lowered for token in ["timeout", "connection", "network", "dns", "ssl", "unreachable"]):
            return "Network error while fetching data. Check your connection and try again."
        if any(token in lowered for token in ["provider", "rate limit", "forbidden", "unauthorized", "api key", "429"]):
            return "Data provider unavailable. Please try again in a moment."
        return f"Error: {text or 'Unknown failure'}"

    def fetch(self) -> None:
        if self._is_fetching:
            return
        s = self.sym.text().strip().upper()
        st = self.st.date().toPython()
        en = self.en.date().toPython()
        if not s or not isinstance(st, date) or not isinstance(en, date) or st >= en:
            self.msg.setText("Invalid input")
            return

        self._is_fetching = True
        self.btn.setEnabled(False)
        self.msg.setText("Fetching data...")
        self._runner.run(self._fetch_data, self._on_fetch_done, self._on_fetch_error, s, st, en)

    def _fetch_data(self, symbol: str, start: date, end: date):
        return self._s.fetch(symbol, start, end)

    def _on_fetch_done(self, result) -> None:
        self._is_fetching = False
        frame = result.frame
        self.t.setRowCount(len(frame))
        for i, (_, x) in enumerate(frame.iterrows()):
            self.t.setItem(i, 0, QTableWidgetItem(str(x.get("Date", ""))))
            self.t.setItem(i, 1, QTableWidgetItem(f"{x.get('Open', 0):.2f}"))
            self.t.setItem(i, 2, QTableWidgetItem(f"{x.get('High', 0):.2f}"))
            self.t.setItem(i, 3, QTableWidgetItem(f"{x.get('Low', 0):.2f}"))
            self.t.setItem(i, 4, QTableWidgetItem(f"{x.get('Close', 0):.2f}"))
            self.t.setItem(i, 5, QTableWidgetItem(f"{x.get('Volume', 0):.0f}"))
        self.btn.setEnabled(True)
        source = getattr(result, "source", "yfinance")
        self.msg.setText(f"Loaded {len(frame)} rows from {source}")

    def _on_fetch_error(self, error: str) -> None:
        self._is_fetching = False
        self.btn.setEnabled(True)
        self.msg.setText(self._friendly_error(error))
