from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from alphaforge.ai.ai_service import AIService
from alphaforge.services.data_service import DataService
from alphaforge.services.view_helpers import correlation_summary, has_valid_date_range, parse_allocations
from alphaforge.ui.ai_worker import AsyncRunner
from alphaforge.ui.views.ai_chat_panel import AIChatPanel


class PortfolioView(QWidget):
    def __init__(self, data_service: DataService, ai_service: AIService, parent=None):
        super().__init__(parent)
        self._data_service = data_service
        self._ai = ai_service
        self._runner = AsyncRunner()
        self._latest_context: dict = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.alloc = QLineEdit("AAPL:0.6,MSFT:0.4")
        self.st = QDateEdit(QDate(2024, 1, 1))
        self.en = QDateEdit(QDate.currentDate())
        self.st.setCalendarPopup(True)
        self.en.setCalendarPopup(True)
        form.addRow("Allocations", self.alloc)
        form.addRow("Start", self.st)
        form.addRow("End", self.en)
        layout.addLayout(form)

        controls = QHBoxLayout()
        self.compute_btn = QPushButton("Compute Risk")
        self.compute_btn.clicked.connect(self.compute)
        self.ai_btn = QPushButton("Analyze portfolio risk")
        self.ai_btn.clicked.connect(self.analyze_ai)
        self.msg = QLabel("Ready")
        controls.addWidget(self.compute_btn)
        controls.addWidget(self.ai_btn)
        controls.addWidget(self.msg, 1)
        layout.addLayout(controls)

        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        layout.addWidget(self.summary)

        self.ai_out = QTextEdit()
        self.ai_out.setReadOnly(True)
        self.ai_out.setPlaceholderText("AI portfolio-risk interpretation will appear here.")
        layout.addWidget(self.ai_out)
        layout.addWidget(AIChatPanel(self._ai, self._get_context))

    def compute(self) -> None:
        st = self.st.date().toPython()
        en = self.en.date().toPython()
        if not has_valid_date_range(st, en):
            self.msg.setText("Invalid input.")
            return

        parsed = self._parse_allocations(self.alloc.text())
        if not parsed:
            self.msg.setText("Use format: AAPL:0.6,MSFT:0.4")
            return

        returns_map: dict[str, pd.Series] = {}
        for symbol in parsed:
            frame = self._data_service.fetch(symbol, st, en).frame
            if frame.empty:
                self.msg.setText(f"No data for {symbol}")
                return
            ordered = frame.sort_values("Date").reset_index(drop=True)
            rets = ordered["Close"].pct_change().fillna(0.0)
            returns_map[symbol] = rets

        returns_df = pd.DataFrame(returns_map).dropna()
        if returns_df.empty:
            self.msg.setText("Not enough overlapping data")
            return

        weights = pd.Series(parsed)
        weights = weights / weights.sum()

        portfolio_returns = returns_df.mul(weights, axis=1).sum(axis=1)
        daily_vol = float(portfolio_returns.std()) if len(portfolio_returns) > 1 else 0.0
        ann_vol_pct = daily_vol * (252**0.5) * 100
        ann_ret_pct = float(portfolio_returns.mean() * 252 * 100)
        sharpe = float((ann_ret_pct / 100) / (ann_vol_pct / 100)) if ann_vol_pct > 1e-9 else 0.0
        equity_curve = (1.0 + portfolio_returns).cumprod()
        drawdown_pct = float((equity_curve / equity_curve.cummax() - 1.0).min() * 100)
        corr = returns_df.corr()
        corr_summary = self._correlation_summary(corr)

        self._latest_context = {
            "portfolio": {
                "allocation_weights": {k: float(v) for k, v in weights.to_dict().items()},
                "symbols": list(weights.index),
            },
            "metrics": {
                "annualized_return_pct": ann_ret_pct,
                "annualized_volatility_pct": ann_vol_pct,
                "sharpe_ratio": sharpe,
                "max_drawdown_pct": drawdown_pct,
            },
            "correlation_summary": corr_summary,
        }

        self.summary.setPlainText(
            f"Annualized Return: {ann_ret_pct:.2f}%\n"
            f"Annualized Volatility: {ann_vol_pct:.2f}%\n"
            f"Sharpe Ratio: {sharpe:.3f}\n"
            f"Max Drawdown: {drawdown_pct:.2f}%\n"
            f"Avg Pairwise Correlation: {corr_summary['average_pairwise_corr']:.3f}\n"
            f"Most Correlated Pair: {corr_summary['top_pair']} ({corr_summary['top_pair_corr']:.3f})"
        )
        self.msg.setText("Risk computed")

    def analyze_ai(self) -> None:
        if not self._latest_context:
            self.msg.setText("Compute risk first")
            return

        self.ai_btn.setEnabled(False)
        self.msg.setText("Generating AI risk analysis...")
        self._runner.run(
            self._ai.analyze_portfolio,
            self._on_ai_done,
            self._on_ai_error,
            self._latest_context,
        )

    def _on_ai_done(self, text: str) -> None:
        self.ai_out.setPlainText(text)
        self.ai_btn.setEnabled(True)
        self.msg.setText("AI risk analysis ready")

    def _on_ai_error(self, error: str) -> None:
        self.ai_out.setPlainText(f"AI error: {error}")
        self.ai_btn.setEnabled(True)
        self.msg.setText("AI unavailable")

    def _get_context(self) -> dict:
        return self._latest_context

    @staticmethod
    def _parse_allocations(text: str) -> dict[str, float]:
        return parse_allocations(text)

    @staticmethod
    def _correlation_summary(corr: pd.DataFrame) -> dict:
        return correlation_summary(corr)
