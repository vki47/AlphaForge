from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
import logging
from pathlib import Path

import pandas as pd

from alphaforge.data.providers.yfinance_provider import (
    DataProviderError,
    PermanentDataProviderError,
    TransientDataProviderError,
    YFinanceProvider,
)


class DataServiceError(Exception):
    """Friendly exception surfaced to calling layers (UI/views)."""


@dataclass
class DataFetchResult:
    frame: pd.DataFrame
    source: str
    symbol: str
    start: date
    end: date
    interval: str


class DataService:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._provider = YFinanceProvider()
        self._logger = logging.getLogger(__name__)

    def fetch(self, symbol: str, start: date, end: date, interval: str = "1d") -> DataFetchResult:
        symbol = (symbol or "").strip().upper()
        cached = self._read_cache(symbol, interval, start, end)

        try:
            frame = self._provider.fetch_ohlcv(symbol, start, end, interval)
        except TransientDataProviderError as exc:
            self._logger.warning(
                "Transient provider error while fetching %s. Falling back to cache when possible.",
                symbol,
                exc_info=exc,
            )
            if not cached.empty:
                return DataFetchResult(cached, "cache", symbol, start, end, interval)
            raise DataServiceError(
                "Unable to reach market data provider right now, and no cached data is available. Please try again shortly."
            )
        except PermanentDataProviderError as exc:
            self._logger.info(
                "Permanent provider error while fetching %s. Falling back to cache when possible.",
                symbol,
                exc_info=exc,
            )
            if not cached.empty:
                return DataFetchResult(cached, "cache", symbol, start, end, interval)
            raise DataServiceError(
                f"Could not fetch market data for {symbol}. Please verify the symbol and selected date range."
            )
        except DataProviderError as exc:
            self._logger.error(
                "Unexpected provider error while fetching %s. Falling back to cache when possible.",
                symbol,
                exc_info=exc,
            )
            if not cached.empty:
                return DataFetchResult(cached, "cache", symbol, start, end, interval)
            raise DataServiceError("Market data provider failed unexpectedly. Please try again.")
        except Exception as exc:  # noqa: BLE001 - normalize uncaught provider errors.
            self._logger.exception("Unhandled fetch exception for %s.", symbol)
            if not cached.empty:
                return DataFetchResult(cached, "cache", symbol, start, end, interval)
            raise DataServiceError(
                "Unable to retrieve market data right now due to an internal data retrieval error."
            ) from exc

        if frame.empty:
            if not cached.empty:
                return DataFetchResult(cached, "cache", symbol, start, end, interval)
            raise DataServiceError(
                f"No market data was returned for {symbol} in the selected date range."
            )

        self._cache(symbol, interval, frame)
        return DataFetchResult(frame, "yfinance", symbol, start, end, interval)

    def _cache(self, symbol: str, interval: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return

        rows = []
        for _, r in frame.iterrows():
            rows.append(
                (
                    symbol.upper(),
                    interval,
                    pd.Timestamp(r["Date"]).date().isoformat(),
                    self._as_float(r.get("Open", 0.0)),
                    self._as_float(r.get("High", 0.0)),
                    self._as_float(r.get("Low", 0.0)),
                    self._as_float(r.get("Close", 0.0)),
                    self._as_float(r.get("Volume", 0.0)),
                )
            )

        try:
            with sqlite3.connect(self._db_path) as c:
                c.executemany(
                    """INSERT INTO price_cache(symbol,interval,date,open,high,low,close,volume)
                                 VALUES (?,?,?,?,?,?,?,?)
                                 ON CONFLICT(symbol,interval,date) DO UPDATE SET
                                 open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,volume=excluded.volume""",
                    rows,
                )
                c.commit()
        except sqlite3.Error as exc:
            self._logger.warning(
                "Failed to cache market data for %s (%s).",
                symbol,
                interval,
                exc_info=exc,
            )

    def _read_cache(self, symbol: str, interval: str, start: date, end: date) -> pd.DataFrame:
        query = """
            SELECT date AS Date, open AS Open, high AS High, low AS Low, close AS Close, volume AS Volume
            FROM price_cache
            WHERE symbol = ? AND interval = ? AND date >= ? AND date < ?
            ORDER BY date ASC
        """
        try:
            with sqlite3.connect(self._db_path) as c:
                frame = pd.read_sql_query(
                    query,
                    c,
                    params=(symbol.upper(), interval, start.isoformat(), end.isoformat()),
                )
        except (sqlite3.Error, pd.errors.DatabaseError) as exc:
            self._logger.warning(
                "Failed to read market-data cache for %s (%s).",
                symbol,
                interval,
                exc_info=exc,
            )
            return self._empty_ohlcv_frame()

        if frame.empty:
            return self._empty_ohlcv_frame()

        frame["Date"] = pd.to_datetime(frame["Date"])
        for column in ["Open", "High", "Low", "Close", "Volume"]:
            if column in frame.columns:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame

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

    def _as_float(self, value: object) -> float:
        if value is None or pd.isna(value):
            return 0.0
        return float(value)
