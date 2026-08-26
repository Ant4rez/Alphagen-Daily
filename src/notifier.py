"""
Notifier — sends the daily briefing via email using Amazon SES.

Design decisions:
- Renders both HTML and plain text; SES sends both, client picks the best.
- HTML uses inline styles (email clients ignore or strip <style> blocks unreliably).
- Wrapped in try/except in the handler: email failure never fails the pipeline.
  The briefing is already persisted to S3/DynamoDB before we get here.
- Fixed max width (~600px) — the de-facto standard for email clients on mobile + desktop.
"""

from __future__ import annotations

from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.models.screening_result import DailyBriefing, ScreeningResult
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ---------- HTML rendering ----------

_HTML_SHELL = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AlphaGen Daily — {run_date}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1f2937;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color:#f4f5f7;padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" style="max-width:600px;background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
          {header}
          {body}
          {footer}
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


_HEADER_TEMPLATE = """\
<tr>
  <td style="padding:24px 32px;background-color:#0f172a;color:#f8fafc;">
    <div style="font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;margin-bottom:4px;">AlphaGen Daily</div>
    <div style="font-size:22px;font-weight:600;color:#f8fafc;">Briefing de {run_date}</div>
    <div style="margin-top:12px;font-size:14px;color:#cbd5e1;">
      {approved_count} de {universe_size} tickers passaram no screening CANSLIM-inspired.
    </div>
  </td>
</tr>"""


_EMPTY_BODY = """\
<tr>
  <td style="padding:32px;font-size:15px;color:#475569;line-height:1.6;">
    Nenhum ticker passou nos filtros hoje. Isso é normal em dias de mercado fraco ou quando os thresholds estão apertados demais. O pipeline rodou com sucesso.
  </td>
</tr>"""


_TICKER_CARD_TEMPLATE = """\
<tr>
  <td style="padding:0 32px;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border-top:1px solid #e5e7eb;padding:24px 0;">
      <tr>
        <td>
          <div style="display:inline-block;font-size:20px;font-weight:700;color:#0f172a;">{symbol}</div>
          <div style="display:inline-block;margin-left:8px;font-size:13px;color:#64748b;">{company_name}</div>
        </td>
        <td align="right">
          <div style="font-size:16px;font-weight:600;color:#0f172a;">${current_price:.2f}</div>
        </td>
      </tr>
      <tr>
        <td colspan="2" style="padding-top:12px;">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="padding-right:16px;font-size:12px;color:#64748b;">
                EPS Q/Q: <span style="color:#059669;font-weight:600;">{eps_qoq}</span>
              </td>
              <td style="padding-right:16px;font-size:12px;color:#64748b;">
                EPS Y/Y: <span style="color:#059669;font-weight:600;">{eps_yoy}</span>
              </td>
              <td style="font-size:12px;color:#64748b;">
                Setor: <span style="color:#1f2937;">{sector}</span>
              </td>
            </tr>
          </table>
        </td>
      </tr>
      <tr>
        <td colspan="2" style="padding-top:16px;font-size:14px;color:#1f2937;line-height:1.6;">
          <div style="font-weight:600;color:#475569;font-size:12px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Tese</div>
          {thesis}
        </td>
      </tr>
      <tr>
        <td colspan="2" style="padding-top:12px;font-size:14px;color:#1f2937;line-height:1.6;">
          <div style="font-weight:600;color:#b45309;font-size:12px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Risco chave</div>
          {key_risk}
        </td>
      </tr>
    </table>
  </td>
</tr>"""


_FOOTER_TEMPLATE = """\
<tr>
  <td style="padding:24px 32px;background-color:#f9fafb;color:#94a3b8;font-size:12px;line-height:1.5;border-top:1px solid #e5e7eb;">
    Este briefing é gerado automaticamente pelo AlphaGen Daily. Análises produzidas por LLM não constituem recomendação de investimento.
    <br><br>
    Gerado em {generated_at} · Modelo: {model_id}
  </td>
</tr>"""


def _format_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.1f}%"


def _render_ticker_card(result: ScreeningResult) -> str:
    ticker = result.ticker
    return _TICKER_CARD_TEMPLATE.format(
        symbol=ticker.symbol,
        company_name=ticker.company_name,
        current_price=ticker.current_price,
        eps_qoq=_format_percent(ticker.eps_growth_qoq),
        eps_yoy=_format_percent(ticker.eps_growth_yoy),
        sector=ticker.sector or "N/A",
        thesis=result.thesis,
        key_risk=result.key_risk,
    )


def render_html(briefing: DailyBriefing) -> str:
    """Render the briefing as an HTML email body."""
    header = _HEADER_TEMPLATE.format(
        run_date=briefing.run_date,
        approved_count=briefing.approved_count,
        universe_size=briefing.universe_size,
    )

    if briefing.approved_count == 0:
        body = _EMPTY_BODY
        model_id = "N/A"
    else:
        body = "".join(_render_ticker_card(r) for r in briefing.results)
        model_id = briefing.results[0].llm_model

    footer = _FOOTER_TEMPLATE.format(
        generated_at=briefing.generated_at,
        model_id=model_id,
    )

    return _HTML_SHELL.format(
        run_date=briefing.run_date,
        header=header,
        body=body,
        footer=footer,
    )


# ---------- Plain text rendering ----------


def render_text(briefing: DailyBriefing) -> str:
    """Render the briefing as a plain text fallback."""
    lines = [
        f"AlphaGen Daily — Briefing de {briefing.run_date}",
        "=" * 60,
        f"{briefing.approved_count} de {briefing.universe_size} tickers passaram no screening.",
        "",
    ]

    if briefing.approved_count == 0:
        lines.append("Nenhum ticker passou nos filtros hoje.")
    else:
        for result in briefing.results:
            t = result.ticker
            lines.extend([
                f"[{t.symbol}] {t.company_name} — ${t.current_price:.2f}",
                f"  Setor: {t.sector or 'N/A'} | EPS Q/Q: {_format_percent(t.eps_growth_qoq)} | EPS Y/Y: {_format_percent(t.eps_growth_yoy)}",
                f"  Tese: {result.thesis}",
                f"  Risco: {result.key_risk}",
                "",
            ])

    lines.extend([
        "-" * 60,
        f"Gerado em {briefing.generated_at}",
        "Análises produzidas por LLM não constituem recomendação de investimento.",
    ])

    return "\n".join(lines)


# ---------- SES invocation ----------


def _build_subject(briefing: DailyBriefing) -> str:
    """Compose a subject line that carries the key info at a glance."""
    return f"AlphaGen Daily — {briefing.run_date}: {briefing.approved_count} aprovados"


def _send_via_ses(
    ses_client: Any,
    sender: str,
    recipients: list[str],
    subject: str,
    html_body: str,
    text_body: str,
) -> str:
    """Invoke SES SendEmail with both HTML and text parts. Returns MessageId."""
    response = ses_client.send_email(
        Source=sender,
        Destination={"ToAddresses": recipients},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Html": {"Data": html_body, "Charset": "UTF-8"},
                "Text": {"Data": text_body, "Charset": "UTF-8"},
            },
        },
    )
    return response.get("MessageId", "")


def send_briefing_email(briefing: DailyBriefing, config: Config) -> None:
    """
    Send the daily briefing as an email via SES.

    Failures are logged and swallowed; email is a nice-to-have that must not
    break the pipeline (the briefing is already persisted to S3/DDB before
    this runs). Callers should still wrap this in a try/except for safety.
    """
    if not config.notify_enabled:
        logger.info("notify disabled, skipping email")
        return

    if not config.ses_sender or not config.ses_recipients:
        logger.warning(
            "notify enabled but sender or recipients missing",
            extra={"sender": config.ses_sender, "recipients_count": len(config.ses_recipients)},
        )
        return

    ses = boto3.client("ses", region_name=config.aws_region)

    subject = _build_subject(briefing)
    html_body = render_html(briefing)
    text_body = render_text(briefing)

    try:
        message_id = _send_via_ses(
            ses_client=ses,
            sender=config.ses_sender,
            recipients=config.ses_recipients,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
        logger.info(
            "briefing email sent",
            extra={
                "message_id": message_id,
                "recipients": config.ses_recipients,
                "approved_count": briefing.approved_count,
            },
        )
    except ClientError as exc:
        logger.error(
            "SES send_email failed",
            extra={"error": str(exc), "recipients": config.ses_recipients},
        )
