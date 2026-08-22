"""
Runtime configuration for AlphaGen Daily.

All configuration comes from environment variables (set via SAM template or local .env).
This module centralizes access so no other module reads os.environ directly.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration."""

    # AWS
    aws_region: str
    s3_bucket: str
    dynamodb_table: str

    # Bedrock
    bedrock_model_id: str
    bedrock_max_tokens: int
    bedrock_temperature: float

    # Screener thresholds (CANSLIM-inspired)
    min_eps_growth_qoq: float       # e.g. 15.0 = 15%
    min_eps_growth_yoy: float       # e.g. 25.0
    max_price: float                # e.g. 50.0
    require_sma_uptrend: bool       # SMA20 > SMA50 > SMA200

    # Runtime
    max_workers: int                # parallel yfinance downloads
    log_level: str


def load_config() -> Config:
    """Load configuration from environment variables with sane defaults."""
    return Config(
        aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        s3_bucket=os.environ.get("S3_BUCKET", "alphagen-daily-briefings"),
        dynamodb_table=os.environ.get("DYNAMODB_TABLE", "alphagen-daily-history"),

        bedrock_model_id=os.environ.get(
            "BEDROCK_MODEL_ID",
            "amazon.nova-lite-v1:0",
        ),
        bedrock_max_tokens=int(os.environ.get("BEDROCK_MAX_TOKENS", "400")),
        bedrock_temperature=float(os.environ.get("BEDROCK_TEMPERATURE", "0.4")),

        min_eps_growth_qoq=float(os.environ.get("MIN_EPS_GROWTH_QOQ", "15.0")),
        min_eps_growth_yoy=float(os.environ.get("MIN_EPS_GROWTH_YOY", "25.0")),
        max_price=float(os.environ.get("MAX_PRICE", "50.0")),
        require_sma_uptrend=os.environ.get("REQUIRE_SMA_UPTREND", "true").lower() == "true",

        max_workers=int(os.environ.get("MAX_WORKERS", "5")),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )