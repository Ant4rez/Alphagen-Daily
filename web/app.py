"""
AlphaGen Daily — Streamlit dashboard (dark premium theme).

Consumes the public API at r0kn41v28a.execute-api.us-east-1.amazonaws.com
and renders the daily briefing with a scrolling ticker tape, per-ticker
cards, and price + SMA charts fetched on demand via yfinance.

Run locally:
    streamlit run app.py

Deploy: Streamlit Cloud, entry point web/app.py.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

# ---------- Configuration ----------

API_BASE = "https://r0kn41v28a.execute-api.us-east-1.amazonaws.com"

# CANSLIM thresholds actually deployed in the SAM template.
# If you change these in template.yaml, mirror the change here so the UI
# panel matches reality until we expose them via a /config endpoint.
DEPLOYED_THRESHOLDS = {
    "min_eps_qoq": 10.0,
    "min_eps_yoy": 15.0,
    "max_price": 500.0,
    "require_sma_uptrend": True,
}

st.set_page_config(
    page_title="AlphaGen Daily",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- Custom CSS (dark premium theme + ticker tape) ----------

CUSTOM_CSS = """
<style>
/* Deep gradient background */
.stApp {
  background: linear-gradient(180deg, #0a0f1e 0%, #0f1729 60%, #0a0f1e 100%);
}

/* Main content padding tweak */
.main .block-container {
  padding-top: 1rem;
  padding-bottom: 3rem;
  max-width: 1300px;
}

/* Headline with cyan gradient */
h1 {
  font-size: 2.4rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.03em;
  background: linear-gradient(90deg, #f8fafc 0%, #22d3ee 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 0.25rem !important;
}

h2, h3 {
  color: #f8fafc !important;
  letter-spacing: -0.01em;
}

/* Caption subtler */
[data-testid="stCaptionContainer"] {
  color: #94a3b8;
}

/* KPI metric cards */
[data-testid="stMetric"] {
  background: rgba(20, 27, 46, 0.55);
  border: 1px solid rgba(34, 211, 238, 0.15);
  border-radius: 12px;
  padding: 16px 20px;
  transition: border-color 0.2s ease;
}
[data-testid="stMetric"]:hover {
  border-color: rgba(34, 211, 238, 0.35);
}
[data-testid="stMetricValue"] {
  font-weight: 700 !important;
  color: #f8fafc !important;
  font-size: 1.8rem !important;
}
[data-testid="stMetricLabel"] p {
  color: #94a3b8 !important;
  font-size: 0.75rem !important;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: 600;
}
[data-testid="stMetricDelta"] {
  color: #22d3ee !important;
  font-weight: 500;
}

/* Ticker card containers (Streamlit's st.container(border=True)) */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: linear-gradient(135deg, rgba(20, 27, 46, 0.7) 0%, rgba(15, 23, 41, 0.9) 100%) !important;
  border: 1px solid rgba(34, 211, 238, 0.12) !important;
  border-radius: 14px !important;
  padding: 24px !important;
  transition: border-color 0.25s ease, transform 0.15s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color: rgba(34, 211, 238, 0.35) !important;
}

/* Expander styling */
details {
  background: rgba(20, 27, 46, 0.5) !important;
  border: 1px solid rgba(31, 41, 55, 0.7) !important;
  border-radius: 10px !important;
}
summary {
  color: #cbd5e1 !important;
  font-weight: 500;
}

/* Divider more subtle */
hr {
  border-color: rgba(31, 41, 55, 0.5) !important;
  margin: 2rem 0 !important;
}

/* Body text */
p, li, .stMarkdown {
  color: #cbd5e1;
}

/* Sidebar background */
[data-testid="stSidebar"] {
  background: rgba(5, 9, 20, 0.95) !important;
  border-right: 1px solid rgba(31, 41, 55, 0.5);
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  color: #f8fafc !important;
}

/* ------ Ticker tape (Bloomberg-style) ------ */
.ticker-wrap {
  overflow: hidden;
  background: linear-gradient(180deg, #050914 0%, #0a1020 100%);
  border-top: 1px solid rgba(34, 211, 238, 0.25);
  border-bottom: 1px solid rgba(34, 211, 238, 0.25);
  padding: 14px 0;
  margin: 0 -100vw 32px -100vw;    /* extend beyond block-container padding */
  padding-left: 100vw;
  padding-right: 100vw;
  white-space: nowrap;
  font-family: 'SF Mono', 'JetBrains Mono', 'Monaco', 'Consolas', monospace;
  font-size: 14px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}
.ticker-track {
  display: inline-block;
  animation: ticker-scroll 60s linear infinite;
  will-change: transform;
}
.ticker-wrap:hover .ticker-track {
  animation-play-state: paused;
}
@keyframes ticker-scroll {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}
.ticker-item {
  display: inline-block;
  padding: 0 28px;
  border-right: 1px solid rgba(31, 41, 55, 0.6);
}
.ticker-symbol {
  color: #f8fafc;
  font-weight: 700;
  letter-spacing: 0.6px;
}
.ticker-price {
  color: #cbd5e1;
  margin-left: 8px;
}
.ticker-delta {
  margin-left: 8px;
  font-weight: 600;
  letter-spacing: 0.3px;
}
.ticker-up   { color: #22c55e; }
.ticker-down { color: #ef4444; }
.ticker-neutral { color: #94a3b8; }
</style>
"""


def render_custom_css() -> None:
    """Inject custom CSS. Must be called after set_page_config, before UI."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------- Data fetching (cached) ----------


@st.cache_data(ttl=300, show_spinner=False)
def fetch_briefing(target_date: str | None = None) -> dict[str, Any] | None:
    """
    Fetch a briefing JSON from the public API.

    Args:
        target_date: YYYY-MM-DD string, or None for the latest briefing.

    Returns:
        The parsed briefing dict, or None if not found / API error.
    """
    url = f"{API_BASE}/today" if target_date is None else f"{API_BASE}/history/{target_date}"

    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException as exc:
        st.error(f"Erro ao buscar briefing: {exc}")
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_price_history(symbol: str, days: int = 240) -> pd.DataFrame | None:
    """
    Download OHLC history for a symbol via yfinance and compute SMAs.
    """
    end = date.today()
    start = end - timedelta(days=days)

    try:
        df = yf.download(
            symbol,
            start=start.isoformat(),
            end=end.isoformat(),
            progress=False,
            auto_adjust=True,
        )
    except Exception as exc:
        st.warning(f"yfinance falhou para {symbol}: {exc}")
        return None

    if df is None or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df["SMA20"] = df["Close"].rolling(window=20).mean()
    df["SMA50"] = df["Close"].rolling(window=50).mean()
    df["SMA200"] = df["Close"].rolling(window=200).mean()

    return df


# ---------- Ticker tape ----------


def render_ticker_tape(results: list[dict[str, Any]]) -> None:
    """
    Render a scrolling ticker tape at the top of the page.

    Uses CSS keyframes to animate a duplicated list of items translating
    from 0 to -50%, which loops seamlessly because the second copy
    occupies the position of the first at the animation reset.
    """
    if not results:
        return

    items_html = []
    for r in results:
        ticker = r["ticker"]
        symbol = ticker["symbol"]
        price = ticker["current_price"]
        eps_yoy = ticker.get("eps_growth_yoy") or 0

        if eps_yoy > 0:
            arrow, cls = "▲", "ticker-up"
        elif eps_yoy < 0:
            arrow, cls = "▼", "ticker-down"
        else:
            arrow, cls = "•", "ticker-neutral"

        items_html.append(
            f'<span class="ticker-item">'
            f'<span class="ticker-symbol">{symbol}</span>'
            f'<span class="ticker-price">${price:.2f}</span>'
            f'<span class="ticker-delta {cls}">{arrow} {eps_yoy:+.1f}%</span>'
            f'</span>'
        )

    # Duplicate the sequence: allows seamless loop with translateX(-50%)
    tape_content = "".join(items_html) * 2

    st.markdown(
        f'<div class="ticker-wrap"><div class="ticker-track">{tape_content}</div></div>',
        unsafe_allow_html=True,
    )


# ---------- Chart rendering ----------


def build_price_sma_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Build a Plotly figure with price and three SMAs (dark theme)."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["Close"], name="Preço",
            line=dict(color="#f8fafc", width=2.2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["SMA20"], name="SMA 20",
            line=dict(color="#22c55e", width=1.4),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["SMA50"], name="SMA 50",
            line=dict(color="#22d3ee", width=1.4),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["SMA200"], name="SMA 200",
            line=dict(color="#f97316", width=1.4),
        )
    )

    fig.update_layout(
        title=dict(
            text=f"{symbol} — Preço e Médias Móveis",
            font=dict(color="#f8fafc", size=15),
        ),
        xaxis_title="",
        yaxis_title="USD",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10, 15, 30, 0.4)",
        hovermode="x unified",
        height=420,
        margin=dict(l=40, r=20, t=50, b=40),
        font=dict(color="#cbd5e1"),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(gridcolor="rgba(31, 41, 55, 0.5)"),
        yaxis=dict(gridcolor="rgba(31, 41, 55, 0.5)"),
    )

    return fig


# ---------- UI sections ----------


def render_header(briefing: dict[str, Any]) -> None:
    """Top-of-page title, subtitle and timestamp."""
    st.title("AlphaGen Daily")
    st.caption(
        "Screening CANSLIM-inspired de ~70 tickers de IA · "
        "Análises geradas por Amazon Bedrock Nova Lite"
    )
    generated_at = briefing.get("generated_at", "")
    if generated_at:
        st.caption(f"📅 Briefing de **{briefing['run_date']}** · gerado às {generated_at[11:19]} UTC")


def render_kpis(briefing: dict[str, Any]) -> None:
    """Three-column KPI row with color-coded metrics."""
    col1, col2, col3 = st.columns(3)
    col1.metric("Data do briefing", briefing["run_date"])
    col2.metric("Universo analisado", f"{briefing['universe_size']} tickers")

    approved = briefing["approved_count"]
    universe = briefing["universe_size"]
    pct = approved / universe if universe else 0
    col3.metric(
        "Aprovados hoje",
        approved,
        delta=f"{pct:.1%} do universo",
        delta_color="off",
    )


def render_parameters_panel() -> None:
    """Expandable panel showing the deployed CANSLIM thresholds."""
    with st.expander("🔧 Parâmetros do screening CANSLIM-inspired", expanded=False):
        st.markdown(
            "**CANSLIM** é um método de análise de ações criado por William O'Neil "
            "combinando fundamentais (crescimento de EPS) com momento técnico (médias móveis). "
            "Nossa versão simplificada usa três dessas dimensões:"
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"**EPS Growth Q/Q ≥ `{DEPLOYED_THRESHOLDS['min_eps_qoq']}%`**\n\n"
                f"Crescimento do lucro por ação vs trimestre anterior — captura aceleração recente."
            )
            st.markdown(
                f"**EPS Growth Y/Y ≥ `{DEPLOYED_THRESHOLDS['min_eps_yoy']}%`**\n\n"
                f"Crescimento anual — filtra empresas com trajetória sustentada, não trimestre isolado."
            )

        with col2:
            st.markdown(
                f"**Preço ≤ `${DEPLOYED_THRESHOLDS['max_price']:.0f}`**\n\n"
                f"Teto configurado alto para não excluir large caps (NVDA, MSFT, GOOGL)."
            )
            st.markdown(
                f"**SMA uptrend obrigatório: `{DEPLOYED_THRESHOLDS['require_sma_uptrend']}`**\n\n"
                f"Requer SMA20 > SMA50 > SMA200 — momento técnico ascendente em três escalas."
            )

        st.markdown(
            "\n_Configurados via env vars no `template.yaml`, ajustáveis sem redeploy de código._"
        )


def render_sidebar(latest_briefing: dict[str, Any] | None) -> tuple[str | None, list[str], str]:
    """Sidebar with date selector and filters."""
    st.sidebar.header("📆 Data")
    mode = st.sidebar.radio(
        "Qual briefing?",
        ["Último disponível", "Data específica"],
        label_visibility="collapsed",
    )

    selected_date_str: str | None = None
    if mode == "Data específica":
        picked = st.sidebar.date_input("Escolha uma data", value=date.today(), max_value=date.today())
        selected_date_str = picked.isoformat()

    st.sidebar.divider()
    st.sidebar.header("🔎 Filtros")

    if latest_briefing and latest_briefing.get("results"):
        sectors = sorted({r["ticker"]["sector"] or "Sem setor" for r in latest_briefing["results"]})
        selected_sectors = st.sidebar.multiselect("Setores", sectors, default=sectors)
    else:
        selected_sectors = []

    selected_sort = st.sidebar.selectbox(
        "Ordenar por",
        [
            "Symbol (A-Z)",
            "Preço (menor primeiro)",
            "Preço (maior primeiro)",
            "EPS Y/Y (maior primeiro)",
            "EPS Q/Q (maior primeiro)",
        ],
    )

    st.sidebar.divider()
    st.sidebar.caption(
        "AlphaGen Daily\n\n"
        "[GitHub](https://github.com/Ant4rez/Alphagen-Daily) · "
        f"[API]({API_BASE}/today)"
    )

    return selected_date_str, selected_sectors, selected_sort


def sort_results(results: list[dict[str, Any]], sort_by: str) -> list[dict[str, Any]]:
    """Sort a list of screening results by the requested key."""
    key_map = {
        "Symbol (A-Z)": lambda r: r["ticker"]["symbol"],
        "Preço (menor primeiro)": lambda r: r["ticker"]["current_price"],
        "Preço (maior primeiro)": lambda r: -r["ticker"]["current_price"],
        "EPS Y/Y (maior primeiro)": lambda r: -(r["ticker"].get("eps_growth_yoy") or 0),
        "EPS Q/Q (maior primeiro)": lambda r: -(r["ticker"].get("eps_growth_qoq") or 0),
    }
    return sorted(results, key=key_map[sort_by])


def _fmt_market_cap(value: float | None) -> str:
    if not value:
        return "N/A"
    if value >= 1e12:
        return f"${value / 1e12:.2f}T"
    if value >= 1e9:
        return f"${value / 1e9:.2f}B"
    return f"${value / 1e6:.0f}M"


def render_ticker_card(result: dict[str, Any]) -> None:
    """Render one ticker card with expandable chart."""
    ticker = result["ticker"]
    symbol = ticker["symbol"]

    with st.container(border=True):
        # Header row: symbol + company + price
        col_left, col_right = st.columns([3, 2])
        with col_left:
            st.markdown(f"### {symbol}")
            company = ticker["company_name"]
            sector = ticker["sector"] or "Sem setor"
            industry = ticker.get("industry") or ""
            caption = f"{company} · {sector}"
            if industry:
                caption += f" · {industry}"
            st.caption(caption)
        with col_right:
            st.metric("Preço", f"${ticker['current_price']:.2f}", label_visibility="collapsed")

        # Metrics row
        col_qoq, col_yoy, col_pe, col_mcap = st.columns(4)
        col_qoq.metric("EPS Q/Q", f"{ticker.get('eps_growth_qoq') or 0:+.1f}%")
        col_yoy.metric("EPS Y/Y", f"{ticker.get('eps_growth_yoy') or 0:+.1f}%")
        pe = ticker.get("pe_ratio")
        col_pe.metric("P/E", f"{pe:.1f}" if pe else "N/A")
        col_mcap.metric("Market Cap", _fmt_market_cap(ticker.get("market_cap")))

        # Thesis + Risk
        st.markdown(f"**💡 Tese:** {result['thesis']}")
        st.markdown(f"**⚠️ Risco chave:** {result['key_risk']}")

        # SMA chart on demand
        with st.expander("📈 Ver preço e médias móveis (últimos 180 dias)"):
            with st.spinner(f"Baixando histórico de {symbol}..."):
                df = fetch_price_history(symbol, days=240)

            if df is None or df.empty:
                st.warning("Histórico de preços não disponível para este ticker.")
            else:
                fig = build_price_sma_chart(df, symbol)
                st.plotly_chart(fig, width="stretch")
                st.caption(
                    "SMA20 > SMA50 > SMA200 é o critério de uptrend do screening. "
                    "Preço acima das três indica momento técnico forte."
                )


def render_ticker_grid(results: list[dict[str, Any]]) -> None:
    """Render tickers in a 2-column grid on wide screens."""
    for i in range(0, len(results), 2):
        cols = st.columns(2, gap="medium")
        with cols[0]:
            render_ticker_card(results[i])
        if i + 1 < len(results):
            with cols[1]:
                render_ticker_card(results[i + 1])


# ---------- Main ----------


def main() -> None:
    """Entry point — renders the whole page."""
    render_custom_css()

    with st.spinner("Carregando briefing..."):
        preliminary = fetch_briefing(target_date=None)

    selected_date, selected_sectors, selected_sort = render_sidebar(preliminary)

    briefing = preliminary if selected_date is None else fetch_briefing(selected_date)

    if briefing is None:
        st.error(
            f"Nenhum briefing encontrado{' para ' + selected_date if selected_date else ''}. "
            "O screener roda em dias úteis às 09:00 BRT — pode ser cedo demais hoje, "
            "ou a data escolhida está fora do histórico."
        )
        return

    # Ticker tape at the very top
    render_ticker_tape(briefing.get("results", []))

    render_header(briefing)
    st.divider()
    render_kpis(briefing)
    render_parameters_panel()
    st.divider()

    # Filter and sort results
    all_results = briefing.get("results", [])
    if selected_sectors:
        filtered = [
            r for r in all_results
            if (r["ticker"]["sector"] or "Sem setor") in selected_sectors
        ]
    else:
        filtered = all_results

    filtered = sort_results(filtered, selected_sort)

    if not filtered:
        st.info("Nenhum ticker corresponde aos filtros selecionados.")
        return

    st.subheader(
        f"🎯 {len(filtered)} ticker(s) aprovado(s)"
        + (f" — filtrado de {len(all_results)}" if len(filtered) < len(all_results) else "")
    )

    render_ticker_grid(filtered)


if __name__ == "__main__":
    main()
