"""
Handler — Lambda entry point for the AlphaGen Daily screener.

Triggered daily by EventBridge Scheduler. Runs the full pipeline:
fetch universe -> screen -> analyze via Bedrock -> persist to S3 + DynamoDB.
"""

from __future__ import annotations

from typing import Any

from src.analyzer import analyze_batch
from src.fetcher import fetch_universe
from src.models.screening_result import DailyBriefing
from src.screener import apply_canslim
from src.storage import persist
from src.universe.ai_tickers import AI_UNIVERSE
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main Lambda handler for the screener pipeline.

    Args:
        event: EventBridge scheduled event payload (unused for now, reserved
               for future features like manual triggers with parameters).
        context: Lambda context object.

    Returns:
        Summary dict with status and briefing metadata.
    """
    config = load_config()

    logger.info(
        "AlphaGen Daily run started",
        extra={
            "universe_size": len(AI_UNIVERSE),
            "min_eps_qoq": config.min_eps_growth_qoq,
            "min_eps_yoy": config.min_eps_growth_yoy,
            "max_price": config.max_price,
            "require_sma_uptrend": config.require_sma_uptrend,
        },
    )

    try:
        # 1) Fetch universe (price history + fundamentals)
        tickers = fetch_universe(AI_UNIVERSE, max_workers=config.max_workers)

        # 2) Apply CANSLIM-inspired screening
        approved = apply_canslim(tickers, config)

        # 3) Analyze each approved ticker via Bedrock
        results = analyze_batch(approved, config)

        # 4) Assemble the daily briefing
        briefing = DailyBriefing.create(
            universe_size=len(AI_UNIVERSE),
            results=results,
        )

        # 5) Persist to S3 + DynamoDB
        persist(briefing, config)

        logger.info(
            "AlphaGen Daily run complete",
            extra={
                "approved_count": briefing.approved_count,
                "run_date": briefing.run_date,
            },
        )

        return {
            "statusCode": 200,
            "body": {
                "run_date": briefing.run_date,
                "universe_size": briefing.universe_size,
                "approved_count": briefing.approved_count,
                "approved_symbols": [r.ticker.symbol for r in briefing.results],
            },
        }

    except Exception as exc:
        logger.error(
            "AlphaGen Daily run failed",
            extra={"error": str(exc), "error_type": type(exc).__name__},
        )
        raise