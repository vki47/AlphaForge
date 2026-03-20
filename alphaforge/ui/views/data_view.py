from __future__ import annotations
from datetime import date
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
from alphaforge.services.data_service import DataService

class DataView(QWidget):
    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent); self._s=data_service; self._build()
    def _build(self):
        l=QVBoxLayout(self); f=QFormLayout()
        self.sym=QLineEdit("AAPL"); self.st=QDateEdit(QDate(2024,1,1)); self.en=QDateEdit(QDate.currentDate())
        self.st.setCalendarPopup(True); self.en.setCalendarPopup(True)
        f.addRow("Symbol",self.sym); f.addRow("Start",self.st); f.addRow("End",self.en); l.addLayout(f)
        a=QHBoxLayout(); self.btn=QPushButton("Fetch Data"); self.btn.clicked.connect(self.fetch); self.msg=QLabel("Ready")
        a.addWidget(self.btn); a.addWidget(self.msg,1); l.addLayout(a)
        self.t=QTableWidget(0,6); self.t.setHorizontalHeaderLabels(["Date","Open","High","Low","Close","Volume"]); l.addWidget(self.t)
    def fetch(self):
        s=self.sym.text().strip().upper(); st=self.st.date().toPython(); en=self.en.date().toPython()
        if not s or not isinstance(st,date) or not isinstance(en,date) or st>=en: self.msg.setText("Invalid input"); return
        try:
            r=self._s.fetch(s,st,en); f=r.frame; self.t.setRowCount(len(f))
            for i,(_,x) in enumerate(f.iterrows()):
                self.t.setItem(i,0,QTableWidgetItem(str(x.get("Date",""))))
                self.t.setItem(i,1,QTableWidgetItem(f"{x.get('Open',0):.2f}"))
                self.t.setItem(i,2,QTableWidgetItem(f"{x.get('High',0):.2f}"))
                self.t.setItem(i,3,QTableWidgetItem(f"{x.get('Low',0):.2f}"))
                self.t.setItem(i,4,QTableWidgetItem(f"{x.get('Close',0):.2f}"))
                self.t.setItem(i,5,QTableWidgetItem(f"{x.get('Volume',0):.0f}"))
            self.msg.setText(f"Loaded {len(f)} rows")
        except Exception as e:
            self.msg.setText(f"Error: {e}")
