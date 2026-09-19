"""
Screener — applies pluggable CANSLIM-inspired filters to the ticker universe.

Design: each filter is a small function registered in FILTERS. The active
filters are chosen at runtime via config.active_filters (env var
ACTIVE_FILTERS, comma-separated list of filter names). Adding a new
filter = adding one entry to FILTERS and one line to its docstring.

Rejection is short-circuit: the first filter a ticker fails on is the one
counted in rejection_reasons. This preserves the "explain why" behavior
without traversing all filters for a rejected ticker.

Missing data on a required field = rejected (conservative default).
"""

from __future__ import annotations

from typing import Callable

from src.models.ticker import Ticker
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


FilterFunc = Callable[[Ticker, Config], bool]


# ---------- Individual filters ----------


def _f_eps_qoq(t: Ticker, c: Config) -> bool:
    """EPS growth Q/Q >= config.min_eps_growth_qoq."""
    return t.eps_growth_qoq is not None and t.eps_growth_qoq >= c.min_eps_growth_qoq


def _f_eps_yoy(t: Ticker, c: Config) -> bool:
    """EPS growth Y/Y >= config.min_eps_growth_yoy."""
    return t.eps_growth_yoy is not None and t.eps_growth_yoy >= c.min_eps_growth_yoy


def _f_price_cap(t: Ticker, c: Config) -> bool:
    """current_price <= config.max_price."""
    return t.current_price is not None and t.current_price <= c.max_price


def _f_sma20_gt_sma50(t: Ticker, c: Config) -> bool:
    """SMA20 > SMA50 (short-term uptrend)."""
    return t.sma_20 is not None and t.sma_50 is not None and t.sma_20 > t.sma_50


def _f_sma50_gt_sma200(t: Ticker, c: Config) -> bool:
    """SMA50 > SMA200 (long-term uptrend)."""
    return t.sma_50 is not None and t.sma_200 is not None and t.sma_50 > t.sma_200


def _f_price_above_sma20(t: Ticker, c: Config) -> bool:
    """Current price > SMA20."""
    return t.current_price is not None and t.sma_20 is not None and t.current_price > t.sma_20


def _f_price_above_sma200(t: Ticker, c: Config) -> bool:
    """Current price > SMA200 (long-term momentum confirmation)."""
    return t.current_price is not None and t.sma_200 is not None and t.current_price > t.sma_200


# ---------- Filter registry ----------

FILTERS: dict[str, FilterFunc] = {
    "eps_qoq": _f_eps_qoq,
    "eps_yoy": _f_eps_yoy,
    "price_cap": _f_price_cap,
    "sma20_gt_sma50": _f_sma20_gt_sma50,
    "sma50_gt_sma200": _f_sma50_gt_sma200,
    "price_above_sma20": _f_price_above_sma20,
    "price_above_sma200": _f_price_above_sma200,
}


# Default filter set equivalent to the historical CANSLIM behavior
# (eps_qoq + eps_yoy + price_cap + SMA20>SMA50>SMA200).
DEFAULT_ACTIVE_FILTERS = [
    "eps_qoq",
    "eps_yoy",
    "price_cap",
    "sma20_gt_sma50",
    "sma50_gt_sma200",
]


# ---------- Screening pipeline ----------


def apply_canslim(tickers: list[Ticker], config: Config) -> list[Ticker]:
    """
    Apply the configured filters and return the passing tickers.

    Args:
        tickers: list of Ticker snapshots.
        config: runtime configuration. Uses config.active_filters to decide
                which filters run, plus per-filter threshold fields.

    Returns:
        List of tickers that passed all active filters.
    """
    if not tickers:
        logger.info("screener received empty ticker list")
        return []

    # Validate active filters against the registry — warn on unknown names,
    # skip them silently so a typo in env var doesn't break the pipeline.
    requested = config.active_filters or DEFAULT_ACTIVE_FILTERS
    unknown = [name for name in requested if name not in FILTERS]
    if unknown:
        logger.warning(
            "unknown filters requested, skipping",
            extra={"unknown": unknown, "available": sorted(FILTERS.keys())},
        )
    active = [name for name in requested if name in FILTERS]

    if not active:
        logger.warning("no valid active filters, approving all tickers")
        return list(tickers)

    logger.info(
        "screening started",
        extra={"input_count": len(tickers), "active_filters": active},
    )

    approved: list[Ticker] = []
    rejection_reasons: dict[str, int] = {name: 0 for name in active}

    for ticker in tickers:
        failed_filter = None
        for name in active:
            if not FILTERS[name](ticker, config):
                failed_filter = name
                break

        if failed_filter:
            rejection_reasons[failed_filter] += 1
        else:
            approved.append(ticker)

    logger.info(
        "screening complete",
        extra={
            "input_count": len(tickers),
            "approved_count": len(approved),
            "rejection_reasons": rejection_reasons,
            "approved_symbols": [t.symbol for t in approved],
            "active_filters": active,
        },
    )

    return approved
