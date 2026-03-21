from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.data.db import init_db
from alphaforge.data.providers.yfinance_provider import PermanentDataProviderError, TransientDataProviderError
from alphaforge.services.data_service import DataService, DataServiceError


class _TransientFailureProvider:
    def fetch_ohlcv(self, symbol, start, end, interval="1d"):
        raise TransientDataProviderError("timeout")


class _PermanentFailureProvider:
    def fetch_ohlcv(self, symbol, start, end, interval="1d"):
        raise PermanentDataProviderError("invalid symbol")


class _EmptyProvider:
    def fetch_ohlcv(self, symbol, start, end, interval="1d"):
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])


class _SuccessProvider:
    def fetch_ohlcv(self, symbol, start, end, interval="1d"):
        return pd.DataFrame(
            [
                {
                    "Date": pd.Timestamp("2024-01-02"),
                    "Open": 100.0,
                    "High": 110.0,
                    "Low": 95.0,
                    "Close": 105.0,
                    "Volume": 1000.0,
                }
            ]
        )


@pytest.fixture
def data_service(tmp_path: Path) -> DataService:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return DataService(db_path)


def test_fetch_falls_back_to_cache_when_provider_temporarily_fails(data_service: DataService):
    start = date(2024, 1, 1)
    end = date(2024, 1, 4)

    data_service._provider = _SuccessProvider()
    data_service.fetch("AAPL", start, end)

    data_service._provider = _TransientFailureProvider()
    result = data_service.fetch("AAPL", start, end)

    assert result.source == "cache"
    assert len(result.frame) == 1


def test_fetch_raises_friendly_error_when_no_cache_and_transient_failure(data_service: DataService):
    data_service._provider = _TransientFailureProvider()

    with pytest.raises(DataServiceError, match="Unable to reach market data provider"):
        data_service.fetch("AAPL", date(2024, 1, 1), date(2024, 1, 4))


def test_fetch_uses_cache_for_empty_provider_response(data_service: DataService):
    start = date(2024, 1, 1)
    end = date(2024, 1, 4)

    data_service._provider = _SuccessProvider()
    data_service.fetch("MSFT", start, end)

    data_service._provider = _EmptyProvider()
    result = data_service.fetch("MSFT", start, end)

    assert result.source == "cache"
    assert not result.frame.empty


def test_fetch_raises_friendly_message_for_empty_data_without_cache(data_service: DataService):
    data_service._provider = _EmptyProvider()

    with pytest.raises(DataServiceError, match="No market data was returned"):
        data_service.fetch("MSFT", date(2024, 1, 1), date(2024, 1, 4))


def test_fetch_uses_cache_for_permanent_failure_when_available(data_service: DataService):
    start = date(2024, 1, 1)
    end = date(2024, 1, 4)

    data_service._provider = _SuccessProvider()
    data_service.fetch("NVDA", start, end)

    data_service._provider = _PermanentFailureProvider()
    result = data_service.fetch("NVDA", start, end)

    assert result.source == "cache"
    assert len(result.frame) == 1
