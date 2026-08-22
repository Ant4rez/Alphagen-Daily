"""
API handler — serves briefings via HTTP endpoints.

Routes:
  GET /today                -> latest briefing JSON
  GET /history/{YYYY-MM-DD} -> briefing for a specific date
"""

from __future__ import annotations

import json
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _response(status: int, body: dict[str, Any] | str) -> dict[str, Any]:
    """Build a normalized API Gateway response."""
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body) if isinstance(body, dict) else body,
    }


def _get_from_s3(key: str, bucket: str, region: str) -> dict[str, Any] | None:
    """Fetch a JSON object from S3 and parse it. Returns None on 404."""
    s3 = boto3.client("s3", region_name=region)

    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(obj["Body"].read())
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code == "NoSuchKey":
            return None
        logger.error("S3 read failed", extra={"key": key, "error": str(exc)})
        return None
    except Exception as exc:
        logger.error("Unexpected S3 read failure", extra={"key": key, "error": str(exc)})
        return None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """API Gateway HTTP handler dispatching to route implementations."""
    config = load_config()
    path = event.get("rawPath", "")

    logger.info("API request received", extra={"path": path})

    # GET /today
    if path == "/today":
        data = _get_from_s3("briefings/latest.json", config.s3_bucket, config.aws_region)
        if data is None:
            return _response(404, {"error": "No briefing found yet. Wait for the first scheduled run."})
        return _response(200, data)

    # GET /history/{YYYY-MM-DD}
    if path.startswith("/history/"):
        date_str = path.replace("/history/", "").strip("/")

        try:
            parts = date_str.split("-")
            if len(parts) != 3:
                raise ValueError("date must be YYYY-MM-DD")
            year, month, day = parts
            key = f"briefings/{year}/{month}/{day}.json"
        except ValueError as exc:
            return _response(400, {"error": f"Invalid date format: {exc}"})

        data = _get_from_s3(key, config.s3_bucket, config.aws_region)
        if data is None:
            return _response(404, {"error": f"No briefing found for date {date_str}"})
        return _response(200, data)

    return _response(404, {"error": f"Route not found: {path}"})