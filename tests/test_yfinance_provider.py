from datetime import date

import pandas as pd
import pytest

from alphaforge.data.providers import yfinance_provider as yp
from alphaforge.data.providers.yfinance_provider import (
    PermanentDataProviderError,
    TransientDataProviderError,
    YFinanceProvider,
)


def test_fetch_ohlcv_retries_transient_error_then_succeeds(monkeypatch):
    provider = YFinanceProvider(max_retries=1, retry_delay_seconds=0)
    calls = {"count": 0}

    class _FakeTicker:
        def history(self, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise TimeoutError("timed out")
            idx = pd.to_datetime(["2024-01-02"])
            idx.name = "Date"
            return pd.DataFrame(
                {
                    "Open": [100.0],
                    "High": [101.0],
                    "Low": [99.0],
                    "Close": [100.5],
                    "Volume": [1234.0],
                },
                index=idx,
            )

    monkeypatch.setattr(yp.yf, "Ticker", lambda symbol: _FakeTicker())
    monkeypatch.setattr(yp.time, "sleep", lambda *_args, **_kwargs: None)

    frame = provider.fetch_ohlcv("aapl", date(2024, 1, 1), date(2024, 1, 3))

    assert calls["count"] == 2
    assert list(frame.columns) == ["Date", "Open", "High", "Low", "Close", "Volume"]
    assert frame.iloc[0]["Date"] == pd.Timestamp("2024-01-02")


def test_fetch_ohlcv_raises_permanent_error_for_invalid_symbol(monkeypatch):
    provider = YFinanceProvider(max_retries=0)

    class _FakeTicker:
        def history(self, **kwargs):
            raise ValueError("symbol not found")

    monkeypatch.setattr(yp.yf, "Ticker", lambda symbol: _FakeTicker())

    with pytest.raises(PermanentDataProviderError, match="rejected"):
        provider.fetch_ohlcv("INVALID", date(2024, 1, 1), date(2024, 1, 3))


def test_fetch_ohlcv_raises_transient_error_after_retries(monkeypatch):
    provider = YFinanceProvider(max_retries=1, retry_delay_seconds=0)

    class _FakeTicker:
        def history(self, **kwargs):
            raise ConnectionError("network down")

    monkeypatch.setattr(yp.yf, "Ticker", lambda symbol: _FakeTicker())
    monkeypatch.setattr(yp.time, "sleep", lambda *_args, **_kwargs: None)

    with pytest.raises(TransientDataProviderError, match="Temporary connectivity issue"):
        provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 3))
