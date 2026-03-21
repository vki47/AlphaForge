from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from alphaforge.ai.ai_service import AIService
from alphaforge.ai.ollama_client import OllamaClient
from alphaforge.services.analysis_service import AnalysisService
from alphaforge.services.backtest_service import BacktestService
from alphaforge.services.bootstrap import bootstrap
from alphaforge.services.data_service import DataService
from alphaforge.ui.views.backtest_view import BacktestView
from alphaforge.ui.views.data_view import DataView
from alphaforge.ui.views.indicators_regime_view import IndicatorsRegimeView
from alphaforge.ui.views.placeholders import PlaceholderView
from alphaforge.ui.views.portfolio_view import PortfolioView


class MainWindow(QMainWindow):
    NAV_ITEMS = [
        "Dashboard",
        "Data",
        "Indicators & Regime",
        "Backtest",
        "Portfolio Risk",
        "Run Compare",
        "Research Report",
        "Settings",
    ]

    def __init__(self, data_service, analysis_service, backtest_service, ai_service):
        super().__init__()
        self._data_service = data_service
        self._analysis_service = analysis_service
        self._backtest_service = backtest_service
        self._ai_service = ai_service
        self.setWindowTitle("AlphaForge — AI Quant Research Copilot")
        self.resize(1280, 840)

        tb = QToolBar("Top")
        tb.setMovable(False)
        tb.addWidget(QLabel("Quant Engine computes values. AI Copilot interprets only structured outputs."))
        self.addToolBar(Qt.TopToolBarArea, tb)

        root = QWidget()
        layout = QVBoxLayout(root)
        nav = QListWidget()
        nav.setMaximumWidth(250)
        pages = QStackedWidget()

        for n in self.NAV_ITEMS:
            nav.addItem(QListWidgetItem(n))
            if n == "Data":
                pages.addWidget(DataView(self._data_service))
            elif n == "Indicators & Regime":
                pages.addWidget(IndicatorsRegimeView(self._analysis_service, self._ai_service))
            elif n == "Backtest":
                pages.addWidget(BacktestView(self._backtest_service, self._ai_service))
            elif n == "Portfolio Risk":
                pages.addWidget(PortfolioView(self._data_service, self._ai_service))
            else:
                pages.addWidget(PlaceholderView(n, f"{n} coming next..."))

        nav.currentRowChanged.connect(pages.setCurrentIndex)
        nav.setCurrentRow(0)

        row = QHBoxLayout()
        row.addWidget(nav)
        row.addWidget(pages, 1)
        layout.addLayout(row)
        self.setCentralWidget(root)


def run_app():
    cfg = bootstrap()
    ds = DataService(cfg.db_path)
    an = AnalysisService(ds)
    bt = BacktestService(an)
    ai = AIService(
        client=OllamaClient(base_url=cfg.ollama_base_url, timeout_seconds=cfg.ollama_timeout_seconds),
        primary_model=cfg.ollama_primary_model,
        fallback_model=cfg.ollama_fallback_model,
    )
    app = QApplication(sys.argv)
    w = MainWindow(ds, an, bt, ai)
    w.show()
    sys.exit(app.exec())
