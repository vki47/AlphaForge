from __future__ import annotations
from datetime import date
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
from alphaforge.services.analysis_service import AnalysisService

class IndicatorsRegimeView(QWidget):
    def __init__(self, analysis_service: AnalysisService, parent=None):
        super().__init__(parent); self._s=analysis_service; self._build()
    def _build(self):
        l=QVBoxLayout(self); f=QFormLayout()
        self.sym=QLineEdit("AAPL"); self.st=QDateEdit(QDate(2024,1,1)); self.en=QDateEdit(QDate.currentDate())
        self.st.setCalendarPopup(True); self.en.setCalendarPopup(True)
        f.addRow("Symbol",self.sym); f.addRow("Start",self.st); f.addRow("End",self.en); l.addLayout(f)
        a=QHBoxLayout(); self.btn=QPushButton("Compute"); self.btn.clicked.connect(self.run); self.msg=QLabel("Ready")
        a.addWidget(self.btn); a.addWidget(self.msg,1); l.addLayout(a)
        self.t=QTableWidget(0,6); self.t.setHorizontalHeaderLabels(["Date","Close","MA Fast","MA Slow","RSI","Regime"]); l.addWidget(self.t)
    def run(self):
        s=self.sym.text().strip().upper(); st=self.st.date().toPython(); en=self.en.date().toPython()
        if not s or not isinstance(st,date) or not isinstance(en,date) or st>=en: self.msg.setText("Invalid input"); return
        r=self._s.run(s,st,en).frame.tail(120).reset_index(drop=True); self.t.setRowCount(len(r))
        for i,(_,x) in enumerate(r.iterrows()):
            self.t.setItem(i,0,QTableWidgetItem(str(x.get("Date",""))))
            self.t.setItem(i,1,QTableWidgetItem(f"{x.get('Close',0):.2f}"))
            self.t.setItem(i,2,QTableWidgetItem(f"{x.get('ma_fast',0):.2f}"))
            self.t.setItem(i,3,QTableWidgetItem(f"{x.get('ma_slow',0):.2f}"))
            self.t.setItem(i,4,QTableWidgetItem(f"{x.get('rsi',0):.2f}"))
            self.t.setItem(i,5,QTableWidgetItem(str(x.get("regime",""))))
        self.msg.setText(f"Computed {len(r)} rows")
