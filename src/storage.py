"""
Storage — persists daily briefings to S3 and DynamoDB.

S3 layout:
  s3://{bucket}/briefings/YYYY/MM/DD.json    (structured JSON, versioned by date)
  s3://{bucket}/briefings/latest.json         (always points to most recent run)

DynamoDB layout:
  PK: run_date (YYYY-MM-DD)
  Attributes: generated_at, universe_size, approved_count, approved_symbols, s3_key, ttl
  TTL: 90 days (auto-cleanup of old runs)
"""

from __future__ import annotations

import json
import time
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.models.screening_result import DailyBriefing
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)

TTL_SECONDS_90_DAYS = 60 * 60 * 24 * 90


def _to_dynamodb_safe(value: Any) -> Any:
    """Recursively convert floats to Decimal for DynamoDB compatibility."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _to_dynamodb_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_dynamodb_safe(v) for v in value]
    return value


def persist_to_s3(briefing: DailyBriefing, config: Config) -> str:
    """
    Write briefing JSON to S3 in two locations: dated path + latest.

    Returns the S3 key of the dated version.
    """
    s3 = boto3.client("s3", region_name=config.aws_region)

    date_parts = briefing.run_date.split("-")  # ["YYYY", "MM", "DD"]
    dated_key = f"briefings/{date_parts[0]}/{date_parts[1]}/{date_parts[2]}.json"
    latest_key = "briefings/latest.json"

    body = json.dumps(briefing.to_dict(), indent=2, default=str).encode("utf-8")

    try:
        s3.put_object(
            Bucket=config.s3_bucket,
            Key=dated_key,
            Body=body,
            ContentType="application/json",
        )
        s3.put_object(
            Bucket=config.s3_bucket,
            Key=latest_key,
            Body=body,
            ContentType="application/json",
        )
        logger.info(
            "briefing persisted to S3",
            extra={"bucket": config.s3_bucket, "dated_key": dated_key, "latest_key": latest_key},
        )
        return dated_key

    except ClientError as exc:
        logger.error("S3 put_object failed", extra={"error": str(exc)})
        raise


def persist_to_dynamodb(briefing: DailyBriefing, s3_key: str, config: Config) -> None:
    """
    Persist briefing metadata to DynamoDB for history and quick lookups.
    """
    ddb = boto3.resource("dynamodb", region_name=config.aws_region)
    table = ddb.Table(config.dynamodb_table)

    item = {
        "run_date": briefing.run_date,
        "generated_at": briefing.generated_at,
        "universe_size": briefing.universe_size,
        "approved_count": briefing.approved_count,
        "approved_symbols": [r.ticker.symbol for r in briefing.results],
        "s3_key": s3_key,
        "ttl": int(time.time()) + TTL_SECONDS_90_DAYS,
    }

    try:
        table.put_item(Item=_to_dynamodb_safe(item))
        logger.info(
            "briefing metadata persisted to DynamoDB",
            extra={"table": config.dynamodb_table, "run_date": briefing.run_date},
        )
    except ClientError as exc:
        logger.error("DynamoDB put_item failed", extra={"error": str(exc)})
        raise


def persist(briefing: DailyBriefing, config: Config) -> None:
    """Persist briefing to both S3 (full JSON) and DynamoDB (metadata)."""
    s3_key = persist_to_s3(briefing, config)
    persist_to_dynamodb(briefing, s3_key, config)