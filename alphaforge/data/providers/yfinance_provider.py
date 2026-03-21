from __future__ import annotations

from datetime import date
import time

import pandas as pd
import yfinance as yf


class DataProviderError(Exception):
    """Base exception for provider-level failures."""


class TransientDataProviderError(DataProviderError):
    """Recoverable provider/network issue that may succeed on retry."""


class PermanentDataProviderError(DataProviderError):
    """Non-recoverable provider issue (e.g., invalid request)."""


class YFinanceProvider:
    def __init__(self, max_retries: int = 2, retry_delay_seconds: float = 0.75) -> None:
        self._max_retries = max_retries
        self._retry_delay_seconds = retry_delay_seconds

    def fetch_ohlcv(self, symbol: str, start: date, end: date, interval: str = "1d") -> pd.DataFrame:
        symbol = (symbol or "").strip().upper()
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                data = yf.Ticker(symbol).history(
                    start=start.isoformat(),
                    end=end.isoformat(),
                    interval=interval,
                    auto_adjust=False,
                )
                return self._normalize_frame(data)
            except Exception as exc:  # noqa: BLE001 - classify unknown provider errors.
                last_error = exc
                if self._is_transient_error(exc) and attempt < self._max_retries:
                    time.sleep(self._retry_delay_seconds * (attempt + 1))
                    continue
                raise self._as_provider_error(symbol, exc) from exc

        raise TransientDataProviderError(
            f"Unable to fetch market data for {symbol} due to repeated network timeouts."
        ) from last_error

    def _normalize_frame(self, data: pd.DataFrame) -> pd.DataFrame:
        if data.empty:
            return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])

        frame = data.reset_index().copy()
        if "Datetime" in frame.columns:
            frame.rename(columns={"Datetime": "Date"}, inplace=True)

        frame["Date"] = pd.to_datetime(frame["Date"]).dt.tz_localize(None)
        columns = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in frame.columns]
        return frame[columns]

    def _as_provider_error(self, symbol: str, exc: Exception) -> DataProviderError:
        if self._is_transient_error(exc):
            return TransientDataProviderError(
                f"Temporary connectivity issue while fetching market data for {symbol}."
            )
        return PermanentDataProviderError(
            f"Market data provider rejected the request for {symbol}."
        )

    def _is_transient_error(self, exc: Exception) -> bool:
        lowered = f"{type(exc).__name__} {exc}".lower()
        transient_tokens = [
            "timeout",
            "timed out",
            "connection",
            "network",
            "temporar",
            "dns",
            "ssl",
            "reset",
            "429",
            "too many requests",
            "rate limit",
            "unavailable",
            "service unavailable",
        ]
        return any(token in lowered for token in transient_tokens)
