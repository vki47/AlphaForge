from __future__ import annotations

from datetime import date
import logging
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
        self._logger = logging.getLogger(__name__)

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
                    delay_seconds = self._retry_delay_seconds * (attempt + 1)
                    self._logger.warning(
                        "Transient market-data fetch failure for %s (%s/%s). Retrying in %.2fs.",
                        symbol,
                        attempt + 1,
                        self._max_retries + 1,
                        delay_seconds,
                        exc_info=exc,
                    )
                    time.sleep(delay_seconds)
                    continue
                self._logger.error(
                    "Market-data fetch failed for %s after %s attempt(s).",
                    symbol,
                    attempt + 1,
                    exc_info=exc,
                )
                raise self._as_provider_error(symbol, exc) from exc

        raise TransientDataProviderError(
            f"Unable to fetch market data for {symbol} due to repeated network timeouts."
        ) from last_error

    def _normalize_frame(self, data: pd.DataFrame) -> pd.DataFrame:
        if data.empty:
            return self._empty_ohlcv_frame()

        frame = data.reset_index().copy()
        if "Datetime" in frame.columns:
            frame.rename(columns={"Datetime": "Date"}, inplace=True)

        frame["Date"] = pd.to_datetime(frame["Date"]).dt.tz_localize(None)
        columns = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in frame.columns]
        normalized = frame[columns].copy()
        for column in ["Open", "High", "Low", "Close", "Volume"]:
            if column in normalized.columns:
                normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        return normalized.reindex(columns=["Date", "Open", "High", "Low", "Close", "Volume"])

    def _empty_ohlcv_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "Date": pd.Series(dtype="datetime64[ns]"),
                "Open": pd.Series(dtype="float64"),
                "High": pd.Series(dtype="float64"),
                "Low": pd.Series(dtype="float64"),
                "Close": pd.Series(dtype="float64"),
                "Volume": pd.Series(dtype="float64"),
            }
        )

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
