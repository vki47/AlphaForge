from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DemoDefaults:
    primary_symbol: str
    compare_symbols: tuple[str, ...]
    start_date: date
    end_date: date
    commission_bps: float
    slippage_bps: float
    report_compare_symbol: str

    @property
    def compare_symbols_text(self) -> str:
        return ",".join(self.compare_symbols)


_DEMO_DEFAULTS = DemoDefaults(
    primary_symbol="AAPL",
    compare_symbols=("AAPL", "MSFT", "NVDA"),
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 31),
    commission_bps=5.0,
    slippage_bps=3.0,
    report_compare_symbol="MSFT",
)


def get_demo_defaults() -> DemoDefaults:
    return _DEMO_DEFAULTS
