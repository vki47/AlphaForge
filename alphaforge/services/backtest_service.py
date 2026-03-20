from __future__ import annotations
from datetime import date
from alphaforge.core.backtester import run_ma_crossover_backtest
from alphaforge.services.analysis_service import AnalysisService

class BacktestService:
    def __init__(self, analysis_service: AnalysisService) -> None:
        self._analysis_service = analysis_service

    def run_ma(self, symbol: str, start: date, end: date, commission_bps: float, slippage_bps: float):
        a = self._analysis_service.run(symbol, start, end)
        return run_ma_crossover_backtest(a.frame, commission_bps, slippage_bps)
