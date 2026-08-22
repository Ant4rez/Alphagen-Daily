"""
Analyzer — sends approved tickers to Amazon Bedrock (Nova Lite) for LLM-based analysis.

Prompt engineering decisions:
- System prompt frames model as a disciplined equity research assistant.
- Structured JSON output requested for parseable, consistent responses.
- Constrained length (thesis 2-3 sentences, risk 1 sentence) to control cost + focus.
- Temperature 0.4 for balance between coherence and slight variation across runs.

Rate limiting:
- Nova Lite has TPS quotas per account. We serialize calls (not parallel)
  and add a short sleep between requests to stay well below throttling limits.
"""

from __future__ import annotations

import json
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.models.screening_result import ScreeningResult
from src.models.ticker import Ticker
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a disciplined equity research assistant specialized in \
AI, semiconductor, cloud data, and enterprise software sectors. You produce concise, \
objective analyses. You never invent numbers. You do NOT give investment advice."""


USER_PROMPT_TEMPLATE = """Analyze the following ticker that passed a CANSLIM-inspired \
technical + fundamental screen:

Ticker: {symbol}
Company: {company_name}
Sector: {sector}
Industry: {industry}

Snapshot:
- Current price: ${current_price:.2f}
- Market cap: {market_cap}
- EPS growth Q/Q: {eps_qoq}
- EPS growth Y/Y: {eps_yoy}
- Forward EPS growth (analyst): {eps_yoy_next}
- P/E ratio: {pe}
- SMA20/50/200: {sma_20}/{sma_50}/{sma_200}

Produce a JSON response with exactly this schema:
{{
  "thesis": "<2 to 3 sentence bullish thesis explaining WHY this ticker passed the screen; \
reference the actual metrics above>",
  "key_risk": "<1 sentence naming the single most relevant risk to monitor>"
}}

Rules:
- Do NOT recommend buy/sell/hold.
- Do NOT invent metrics that were not provided.
- Do NOT include markdown fences or any text outside the JSON.
- Keep total response under 300 characters."""


def _format_number(value: float | None, prefix: str = "", suffix: str = "") -> str:
    if value is None:
        return "N/A"
    if suffix == "%":
        return f"{prefix}{value:.1f}{suffix}"
    if abs(value) >= 1_000_000_000:
        return f"{prefix}${value / 1_000_000_000:.1f}B"
    return f"{prefix}{value:.2f}{suffix}"


def _build_user_prompt(ticker: Ticker) -> str:
    return USER_PROMPT_TEMPLATE.format(
        symbol=ticker.symbol,
        company_name=ticker.company_name,
        sector=ticker.sector or "N/A",
        industry=ticker.industry or "N/A",
        current_price=ticker.current_price,
        market_cap=_format_number(ticker.market_cap),
        eps_qoq=_format_number(ticker.eps_growth_qoq, suffix="%"),
        eps_yoy=_format_number(ticker.eps_growth_yoy, suffix="%"),
        eps_yoy_next=_format_number(ticker.eps_growth_yoy_next, suffix="%"),
        pe=_format_number(ticker.pe_ratio),
        sma_20=_format_number(ticker.sma_20),
        sma_50=_format_number(ticker.sma_50),
        sma_200=_format_number(ticker.sma_200),
    )


def _invoke_nova(
    bedrock_client: Any,
    model_id: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """
    Invoke Amazon Nova via Bedrock Converse API.

    Returns the raw text response from the model.
    """
    response = bedrock_client.converse(
        modelId=model_id,
        system=[{"text": system_prompt}],
        messages=[
            {
                "role": "user",
                "content": [{"text": user_prompt}],
            }
        ],
        inferenceConfig={
            "maxTokens": max_tokens,
            "temperature": temperature,
        },
    )

    return response["output"]["message"]["content"][0]["text"]


def _parse_llm_response(raw_text: str, symbol: str) -> tuple[str, str]:
    """
    Parse the JSON response from the LLM.

    Returns (thesis, key_risk). Falls back to defensive strings if parsing fails.
    """
    try:
        # Strip potential whitespace and extract JSON
        stripped = raw_text.strip()
        # Some models occasionally wrap in markdown despite instructions
        if stripped.startswith("```"):
            stripped = stripped.split("```")[1]
            if stripped.startswith("json"):
                stripped = stripped[4:]
            stripped = stripped.strip()

        payload = json.loads(stripped)
        thesis = str(payload.get("thesis", "")).strip()
        key_risk = str(payload.get("key_risk", "")).strip()

        if not thesis or not key_risk:
            raise ValueError("empty thesis or key_risk field")

        return thesis, key_risk

    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.warning(
            "LLM response parse failed, using fallback",
            extra={"symbol": symbol, "error": str(exc), "raw": raw_text[:200]},
        )
        return (
            "Passed CANSLIM-inspired screening on EPS growth and price momentum.",
            "Automated analysis unavailable; review manually before acting.",
        )


def analyze_ticker(
    ticker: Ticker,
    bedrock_client: Any,
    config: Config,
) -> ScreeningResult:
    """Analyze a single ticker via Bedrock and return a ScreeningResult."""
    user_prompt = _build_user_prompt(ticker)

    try:
        raw = _invoke_nova(
            bedrock_client=bedrock_client,
            model_id=config.bedrock_model_id,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=config.bedrock_max_tokens,
            temperature=config.bedrock_temperature,
        )
        thesis, key_risk = _parse_llm_response(raw, ticker.symbol)

    except ClientError as exc:
        logger.error(
            "Bedrock invocation failed",
            extra={"symbol": ticker.symbol, "error": str(exc)},
        )
        thesis = "Automated analysis temporarily unavailable."
        key_risk = "Bedrock invocation failed; review manually."

    return ScreeningResult(
        ticker=ticker,
        thesis=thesis,
        key_risk=key_risk,
        llm_model=config.bedrock_model_id,
    )


def analyze_batch(
    tickers: list[Ticker],
    config: Config,
    request_delay_seconds: float = 0.5,
) -> list[ScreeningResult]:
    """
    Analyze a batch of approved tickers.

    Serializes calls with a small delay to respect Bedrock TPS limits.
    """
    if not tickers:
        logger.info("analyzer received empty ticker list")
        return []

    bedrock = boto3.client("bedrock-runtime", region_name=config.aws_region)

    results: list[ScreeningResult] = []
    for i, ticker in enumerate(tickers):
        logger.info("analyzing ticker", extra={"symbol": ticker.symbol, "index": i + 1, "total": len(tickers)})
        result = analyze_ticker(ticker, bedrock, config)
        results.append(result)

        if i < len(tickers) - 1:
            time.sleep(request_delay_seconds)

    logger.info("analysis batch complete", extra={"analyzed_count": len(results)})
    return results