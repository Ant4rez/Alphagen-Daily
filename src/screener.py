"""
Screener — applies CANSLIM-inspired filters to the ticker universe.

Filters applied (all configurable via Config):
  1. EPS growth Q/Q >= threshold (default 15%)
  2. EPS growth Y/Y >= threshold (default 25%)
  3. Current price <= max_price (default $50)
  4. SMA uptrend: SMA20 > SMA50 > SMA200 (optional)

Tickers with missing data on a required filter are excluded (conservative default).
"""

from __future__ import annotations

from src.models.ticker import Ticker
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _passes_eps_qoq(ticker: Ticker, threshold: float) -> bool:
    return ticker.eps_growth_qoq is not None and ticker.eps_growth_qoq >= threshold


def _passes_eps_yoy(ticker: Ticker, threshold: float) -> bool:
    return ticker.eps_growth_yoy is not None and ticker.eps_growth_yoy >= threshold


def _passes_price(ticker: Ticker, max_price: float) -> bool:
    return ticker.current_price is not None and ticker.current_price <= max_price


def _passes_sma_uptrend(ticker: Ticker) -> bool:
    return ticker.has_sma_uptrend


def apply_canslim(tickers: list[Ticker], config: Config) -> list[Ticker]:
    """
    Apply CANSLIM-inspired filters and return the passing tickers.

    Args:
        tickers: list of Ticker snapshots.
        config: runtime configuration with thresholds.

    Returns:
        List of tickers that passed all active filters.
    """
    if not tickers:
        logger.info("screener received empty ticker list")
        return []

    approved: list[Ticker] = []
    rejection_reasons: dict[str, int] = {
        "eps_qoq": 0,
        "eps_yoy": 0,
        "price": 0,
        "sma_uptrend": 0,
    }

    for ticker in tickers:
        if not _passes_eps_qoq(ticker, config.min_eps_growth_qoq):
            rejection_reasons["eps_qoq"] += 1
            continue

        if not _passes_eps_yoy(ticker, config.min_eps_growth_yoy):
            rejection_reasons["eps_yoy"] += 1
            continue

        if not _passes_price(ticker, config.max_price):
            rejection_reasons["price"] += 1
            continue

        if config.require_sma_uptrend and not _passes_sma_uptrend(ticker):
            rejection_reasons["sma_uptrend"] += 1
            continue

        approved.append(ticker)

    logger.info(
        "screening complete",
        extra={
            "input_count": len(tickers),
            "approved_count": len(approved),
            "rejection_reasons": rejection_reasons,
            "approved_symbols": [t.symbol for t in approved],
        },
    )

    return approved