"""
Screening result — the ticker payload after LLM analysis, ready for storage.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any

from src.models.ticker import Ticker


@dataclass
class ScreeningResult:
    """A ticker that passed screening, enriched with LLM analysis."""

    ticker: Ticker
    thesis: str                      # 2-3 sentence bullish thesis
    key_risk: str                    # single risk factor to watch
    llm_model: str                   # which model generated the analysis

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker.to_dict(),
            "thesis": self.thesis,
            "key_risk": self.key_risk,
            "llm_model": self.llm_model,
        }


@dataclass
class DailyBriefing:
    """The full output of one screening run."""

    run_date: str                            # YYYY-MM-DD
    generated_at: str                        # ISO 8601 UTC
    universe_size: int                       # tickers analyzed
    approved_count: int                      # tickers that passed
    results: list[ScreeningResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, universe_size: int, results: list[ScreeningResult]) -> "DailyBriefing":
        now = datetime.now(timezone.utc)
        return cls(
            run_date=now.date().isoformat(),
            generated_at=now.isoformat(),
            universe_size=universe_size,
            approved_count=len(results),
            results=results,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_date": self.run_date,
            "generated_at": self.generated_at,
            "universe_size": self.universe_size,
            "approved_count": self.approved_count,
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata,
        }