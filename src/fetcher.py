"""
Fetcher — downloads market data + fundamentals from yfinance.

Design decisions:
- Uses yfinance.download() batch for price history.
- Fetches fundamentals ticker-by-ticker serially with a small delay to
  respect Yahoo's implicit rate limits (works on datacenter IPs like Lambda).
- Silently skips tickers that fail rather than crashing the whole run.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

from src.models.ticker import Ticker
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Small delay between per-ticker fundamentals calls to avoid rate limiting
_INTER_REQUEST_DELAY_SECONDS = 0.35


def _safe_get(info: dict[str, Any], key: str, default: Any = None) -> Any:
    value = info.get(key, default)
    if value == "" or value is None:
        return default
    return value


def _to_percent(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value) * 100
    except (TypeError, ValueError):
        return None


def _compute_sma(prices: pd.Series, window: int) -> float | None:
    if len(prices) < window:
        return None
    sma = prices.rolling(window=window).mean().iloc[-1]
    return float(sma) if pd.notna(sma) else None


def _extract_symbol_history(
    history: pd.DataFrame,
    symbol: str,
    single_ticker: bool,
) -> pd.DataFrame | None:
    try:
        if single_ticker:
            return history

        if symbol not in history.columns.get_level_values(0):
            logger.warning("ticker not in price history batch", extra={"symbol": symbol})
            return None

        symbol_df = history[symbol]
        if not isinstance(symbol_df, pd.DataFrame):
            logger.warning("unexpected type for symbol history", extra={"symbol": symbol})
            return None

        return symbol_df

    except (KeyError, AttributeError) as exc:
        logger.warning(
            "failed to extract symbol history",
            extra={"symbol": symbol, "error": str(exc)},
        )
        return None


def _fetch_single(symbol: str, price_history: pd.DataFrame) -> Ticker | None:
    try:
        yf_ticker = yf.Ticker(symbol)
        info = yf_ticker.info

        if not info or "regularMarketPrice" not in info:
            logger.warning("skipping ticker: no info returned", extra={"symbol": symbol})
            return None

        close = price_history["Close"]
        if close.empty:
            logger.warning("skipping ticker: empty price history", extra={"symbol": symbol})
            return None

        current_price = float(close.iloc[-1])

        return Ticker(
            symbol=symbol,
            company_name=_safe_get(info, "longName", symbol),
            sector=_safe_get(info, "sector"),
            industry=_safe_get(info, "industry"),
            current_price=current_price,
            sma_20=_compute_sma(close, 20),
            sma_50=_compute_sma(close, 50),
            sma_200=_compute_sma(close, 200),
            market_cap=_safe_get(info, "marketCap"),
            eps_growth_qoq=_to_percent(_safe_get(info, "earningsQuarterlyGrowth")),
            eps_growth_yoy=_to_percent(_safe_get(info, "earningsGrowth")),
            eps_growth_yoy_next=_to_percent(_safe_get(info, "earningsForwardGrowth")),
            pe_ratio=_safe_get(info, "trailingPE"),
        )

    except Exception as exc:
        logger.warning(
            "ticker fetch failed",
            extra={"symbol": symbol, "error": str(exc)},
        )
        return None


def fetch_universe(symbols: list[str], max_workers: int = 1) -> list[Ticker]:
    """
    Download price history + fundamentals for a list of symbols.

    Note: max_workers is kept for API compatibility but ignored — we fetch
    fundamentals serially with a small delay to avoid Yahoo rate limiting
    from datacenter IPs.
    """
    if not symbols:
        return []

    logger.info("starting universe fetch", extra={"symbol_count": len(symbols)})

    # 1) Batch download price history (single HTTP call)
    end = datetime.now()
    start = end - timedelta(days=300)

    logger.info("downloading price history batch")
    history = yf.download(
        tickers=symbols,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        progress=False,
        group_by="ticker",
        auto_adjust=True,
        threads=False,
    )

    if history is None or history.empty:
        logger.error("batch price download returned empty or None DataFrame")
        return []

    # 2) Serial fetch of fundamentals with delay
    tickers: list[Ticker] = []
    single_ticker = len(symbols) == 1

    for i, symbol in enumerate(symbols):
        symbol_history = _extract_symbol_history(history, symbol, single_ticker)
        if symbol_history is None:
            continue

        if symbol_history["Close"].dropna().empty:
            logger.warning("ticker has no close prices", extra={"symbol": symbol})
            continue

        result = _fetch_single(symbol, symbol_history)
        if result is not None:
            tickers.append(result)

        # Small delay between requests to be gentle with Yahoo
        if i < len(symbols) - 1:
            time.sleep(_INTER_REQUEST_DELAY_SECONDS)

    logger.info(
        "universe fetch complete",
        extra={
            "requested": len(symbols),
            "fetched": len(tickers),
            "failed": len(symbols) - len(tickers),
        },
    )
    return tickers