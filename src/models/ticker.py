"""
Ticker data model — snapshot of a single stock at screening time.

Kept as a plain dataclass so it serializes cleanly to JSON for S3 storage
and DynamoDB persistence without ORM overhead.
"""

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class Ticker:
    """A single ticker's snapshot used by the screener."""

    symbol: str
    company_name: str
    sector: str | None
    industry: str | None

    # Price
    current_price: float
    sma_20: float | None
    sma_50: float | None
    sma_200: float | None

    # Fundamentals
    market_cap: float | None
    eps_growth_qoq: float | None      # percentage
    eps_growth_yoy: float | None      # percentage
    eps_growth_yoy_next: float | None # analyst forward estimate
    pe_ratio: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def has_sma_uptrend(self) -> bool:
        """True if SMA20 > SMA50 > SMA200 (all present)."""
        if self.sma_20 is None or self.sma_50 is None or self.sma_200 is None:
            return False
        return self.sma_20 > self.sma_50 > self.sma_200