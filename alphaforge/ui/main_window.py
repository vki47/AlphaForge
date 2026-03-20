from __future__ import annotations
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QListWidget, QListWidgetItem, QMainWindow, QStackedWidget, QHBoxLayout, QVBoxLayout, QWidget, QToolBar
from alphaforge.services.bootstrap import bootstrap
from alphaforge.services.data_service import DataService
from alphaforge.services.analysis_service import AnalysisService
from alphaforge.services.backtest_service import BacktestService
from alphaforge.ui.views.data_view import DataView
from alphaforge.ui.views.indicators_regime_view import IndicatorsRegimeView
from alphaforge.ui.views.backtest_view import BacktestView
from alphaforge.ui.views.placeholders import PlaceholderView

class MainWindow(QMainWindow):
    NAV_ITEMS = ["Dashboard","Data","Indicators & Regime","Backtest","Portfolio Risk","Run Compare","Research Report","Settings"]
    def __init__(self, data_service, analysis_service, backtest_service):
        super().__init__()
        self._data_service = data_service
        self._analysis_service = analysis_service
        self._backtest_service = backtest_service
        self.setWindowTitle("AlphaForge — AI Quant Research Copilot")
        self.resize(1200, 780)

        tb = QToolBar("Top")
        tb.setMovable(False)
        tb.addWidget(QLabel("Symbol/Date controls will appear per module"))
        self.addToolBar(Qt.TopToolBarArea, tb)

        root = QWidget(); layout = QVBoxLayout(root)
        nav = QListWidget(); nav.setMaximumWidth(250)
        pages = QStackedWidget()
        for n in self.NAV_ITEMS:
            nav.addItem(QListWidgetItem(n))
            if n == "Data":
                pages.addWidget(DataView(self._data_service))
            elif n == "Indicators & Regime":
                pages.addWidget(IndicatorsRegimeView(self._analysis_service))
            elif n == "Backtest":
                pages.addWidget(BacktestView(self._backtest_service))
            else:
                pages.addWidget(PlaceholderView(n, f"{n} coming next..."))
        nav.currentRowChanged.connect(pages.setCurrentIndex)
        nav.setCurrentRow(0)

        row = QHBoxLayout(); row.addWidget(nav); row.addWidget(pages, 1)
        layout.addLayout(row)
        self.setCentralWidget(root)

def run_app():
    cfg = bootstrap()
    ds = DataService(cfg.db_path)
    an = AnalysisService(ds)
    bt = BacktestService(an)
    app = QApplication(sys.argv)
    w = MainWindow(ds, an, bt)
    w.show()
    sys.exit(app.exec())
