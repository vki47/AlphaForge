from __future__ import annotations
from datetime import date
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit,QDoubleSpinBox,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QTextEdit,QVBoxLayout,QWidget
from alphaforge.services.backtest_service import BacktestService

class BacktestView(QWidget):
    def __init__(self, backtest_service: BacktestService, parent=None):
        super().__init__(parent); self._s=backtest_service; self._build()
    def _build(self):
        l=QVBoxLayout(self); f=QFormLayout()
        self.sym=QLineEdit("AAPL"); self.st=QDateEdit(QDate(2024,1,1)); self.en=QDateEdit(QDate.currentDate())
        self.st.setCalendarPopup(True); self.en.setCalendarPopup(True)
        self.c=QDoubleSpinBox(); self.c.setRange(0,200); self.c.setValue(5); self.c.setSuffix(" bps")
        self.sl=QDoubleSpinBox(); self.sl.setRange(0,200); self.sl.setValue(3); self.sl.setSuffix(" bps")
        f.addRow("Symbol",self.sym); f.addRow("Start",self.st); f.addRow("End",self.en); f.addRow("Commission",self.c); f.addRow("Slippage",self.sl)
        l.addLayout(f)
        a=QHBoxLayout(); self.btn=QPushButton("Run MA Backtest"); self.btn.clicked.connect(self.run); self.msg=QLabel("Ready")
        a.addWidget(self.btn); a.addWidget(self.msg,1); l.addLayout(a)
        self.out=QTextEdit(); self.out.setReadOnly(True); l.addWidget(self.out)
    def run(self):
        s=self.sym.text().strip().upper(); st=self.st.date().toPython(); en=self.en.date().toPython()
        if not s or not isinstance(st,date) or not isinstance(en,date) or st>=en: self.msg.setText("Invalid input"); return
        r=self._s.run_ma(s,st,en,float(self.c.value()),float(self.sl.value()))
        self.out.setPlainText(
            f"Total Return: {r.total_return_pct:.2f}%\n"
            f"Annualized Return: {r.annualized_return_pct:.2f}%\n"
            f"Annualized Volatility: {r.annualized_vol_pct:.2f}%\n"
            f"Sharpe: {r.sharpe:.3f}\n"
            f"Max Drawdown: {r.max_drawdown_pct:.2f}%"
        )
        self.msg.setText("Backtest complete")
