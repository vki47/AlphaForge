from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import pandas as pd
from alphaforge.core.indicators import compute_indicators
from alphaforge.core.regimes import classify_regime
from alphaforge.services.data_service import DataService

@dataclass
class AnalysisResult:
    frame: pd.DataFrame

class AnalysisService:
    def __init__(self, data_service: DataService) -> None:
        self._data_service = data_service

    def run(self, symbol: str, start: date, end: date) -> AnalysisResult:
        raw = self._data_service.fetch(symbol, start, end).frame
        return AnalysisResult(classify_regime(compute_indicators(raw)))
