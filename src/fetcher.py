"""
Fetcher — downloads market data + fundamentals from yfinance.

Design decisions:
- Uses yfinance.download() for batch price history (single HTTP call).
- Falls back to per-ticker fetching for fundamentals (yfinance limitation).
- Uses ThreadPoolExecutor to parallelize fundamental fetches.
- Silently skips tickers that fail to fetch (delisted, symbol change, etc)
  rather than crashing the whole run.
"""

from __future__ import annotations

import concurrent.futures as cf
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

from src.models.ticker import Ticker
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _safe_get(info: dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely extract a key from yfinance info dict."""
    value = info.get(key, default)
    if value == "" or value is None:
        return default
    return value


def _to_percent(value: Any) -> float | None:
    """Convert a fraction from yfinance (e.g. 0.15) to percentage (15.0)."""
    if value is None:
        return None
    try:
        return float(value) * 100
    except (TypeError, ValueError):
        return None


def _compute_sma(prices: pd.Series, window: int) -> float | None:
    """Return the most recent SMA value for the given window, or None if insufficient data."""
    if len(prices) < window:
        return None
    sma = prices.rolling(window=window).mean().iloc[-1]
    return float(sma) if pd.notna(sma) else None


def _fetch_single(symbol: str, price_history: pd.DataFrame) -> Ticker | None:
    """
    Fetch fundamentals for a single ticker and combine with pre-fetched price history.

    Returns None if fetch fails at any critical step.
    """
    try:
        yf_ticker = yf.Ticker(symbol)
        info = yf_ticker.info

        if not info or "regularMarketPrice" not in info:
            logger.warning("skipping ticker: no info returned", extra={"symbol": symbol})
            return None

        # Extract close prices for SMAs
        close = price_history["Close"] if isinstance(price_history, pd.Series) else price_history["Close"]
        if close.empty:
            logger.warning("skipping ticker: empty price history", extra={"symbol": symbol})
            return None

        current_price = float(close.iloc[-1])

        ticker = Ticker(
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

        return ticker

    except Exception as exc:
        logger.warning(
            "ticker fetch failed",
            extra={"symbol": symbol, "error": str(exc)},
        )
        return None


def fetch_universe(symbols: list[str], max_workers: int = 10) -> list[Ticker]:
    """
    Download price history + fundamentals for a list of symbols.

    Args:
        symbols: list of ticker symbols (e.g. ["NVDA", "MSFT"]).
        max_workers: parallelism for fundamentals fetching.

    Returns:
        List of Ticker objects (skipping any that failed to fetch).
    """
    if not symbols:
        return []

    logger.info("starting universe fetch", extra={"symbol_count": len(symbols)})

    # 1) Batch download 250 days of price history (single HTTP call)
    end = datetime.now()
    start = end - timedelta(days=300)  # buffer for weekends/holidays

    logger.info("downloading price history batch")
    history = yf.download(
        tickers=symbols,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        progress=False,
        group_by="ticker",
        auto_adjust=True,
        threads=True,
    )

    if history.empty:
        logger.error("batch price download returned empty DataFrame")
        return []

    # 2) Parallel fetch of fundamentals + assembly
    tickers: list[Ticker] = []

    with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for symbol in symbols:
            try:
                symbol_history = history[symbol] if len(symbols) > 1 else history
                if symbol_history["Close"].dropna().empty:
                    continue
                futures[executor.submit(_fetch_single, symbol, symbol_history)] = symbol
            except KeyError:
                logger.warning("ticker not in price history", extra={"symbol": symbol})
                continue

        for future in cf.as_completed(futures):
            result = future.result()
            if result is not None:
                tickers.append(result)

    logger.info(
        "universe fetch complete",
        extra={
            "requested": len(symbols),
            "fetched": len(tickers),
            "failed": len(symbols) - len(tickers),
        },
    )
    return tickers