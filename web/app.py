"""
AlphaGen Daily — Streamlit dashboard.

Consumes the public API at r0kn41v28a.execute-api.us-east-1.amazonaws.com
and renders the daily briefing with per-ticker price + SMA charts fetched
on demand via yfinance.

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

    Args:
        symbol: ticker symbol (e.g. "NVDA").
        days: how many calendar days back to fetch.

    Returns:
        DataFrame indexed by date with columns Close, SMA20, SMA50, SMA200.
        None if fetch failed or returned empty.
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

    # yfinance sometimes returns multi-level columns (ticker as second level)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Compute simple moving averages
    df["SMA20"] = df["Close"].rolling(window=20).mean()
    df["SMA50"] = df["Close"].rolling(window=50).mean()
    df["SMA200"] = df["Close"].rolling(window=200).mean()

    return df


# ---------- Chart rendering ----------


def build_price_sma_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Build a Plotly figure with price and three SMAs."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            name="Preço",
            line=dict(color="#0f172a", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SMA20"],
            name="SMA 20",
            line=dict(color="#059669", width=1.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SMA50"],
            name="SMA 50",
            line=dict(color="#3b82f6", width=1.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SMA200"],
            name="SMA 200",
            line=dict(color="#dc2626", width=1.5),
        )
    )

    fig.update_layout(
        title=f"{symbol} — Preço e Médias Móveis (últimos {len(df)} pregões)",
        xaxis_title="Data",
        yaxis_title="Preço (USD)",
        template="plotly_white",
        hovermode="x unified",
        height=420,
        margin=dict(l=40, r=20, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


# ---------- UI sections ----------


def render_header(briefing: dict[str, Any]) -> None:
    """Top-of-page title and description."""
    st.title("AlphaGen Daily")
    st.caption(
        "Screening CANSLIM-inspired de ~70 tickers de IA · "
        "Análise gerada por Amazon Bedrock Nova Lite · "
        f"Briefing de **{briefing['run_date']}**"
    )


def render_kpis(briefing: dict[str, Any]) -> None:
    """Three-column KPI row."""
    col1, col2, col3 = st.columns(3)
    col1.metric("Data do briefing", briefing["run_date"])
    col2.metric("Universo analisado", briefing["universe_size"])
    col3.metric(
        "Tickers aprovados",
        briefing["approved_count"],
        delta=f"{briefing['approved_count'] / briefing['universe_size']:.1%}",
        delta_color="off",
    )


def render_parameters_panel() -> None:
    """Expandable panel showing the deployed CANSLIM thresholds."""
    with st.expander("🔧 Parâmetros do screening (CANSLIM-inspired)", expanded=False):
        st.markdown(
            "Estes são os thresholds em produção. Para ajustar, edite `template.yaml` "
            "sob `Globals.Function.Environment.Variables` e rode `sam deploy`."
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"**EPS Growth Q/Q mínimo:** `{DEPLOYED_THRESHOLDS['min_eps_qoq']}%`\n\n"
                f"Crescimento do lucro por ação trimestre vs trimestre anterior. "
                f"Filtra empresas com aceleração recente de lucro."
            )
            st.markdown(
                f"**EPS Growth Y/Y mínimo:** `{DEPLOYED_THRESHOLDS['min_eps_yoy']}%`\n\n"
                f"Crescimento do lucro por ação ano vs ano anterior. "
                f"Filtra empresas com trajetória sustentada, não só um trimestre isolado."
            )

        with col2:
            st.markdown(
                f"**Preço máximo:** `${DEPLOYED_THRESHOLDS['max_price']:.0f}`\n\n"
                f"Teto de preço por ação. Configurado alto para não excluir large caps de IA "
                f"(NVDA, MSFT, GOOGL) que negociam acima de $100."
            )
            st.markdown(
                f"**SMA uptrend obrigatório:** `{DEPLOYED_THRESHOLDS['require_sma_uptrend']}`\n\n"
                f"Exige que SMA20 > SMA50 > SMA200 (momento técnico ascendente em três "
                f"escalas). Aprovado só se as três médias estiverem alinhadas para cima."
            )


def render_sidebar(latest_briefing: dict[str, Any] | None) -> tuple[str | None, list[str], str]:
    """
    Sidebar with date selector and filters.

    Returns:
        (selected_date_str, selected_sectors, selected_sort)
        selected_date_str is None when user picks "latest".
    """
    st.sidebar.header("Data")

    mode = st.sidebar.radio(
        "Qual briefing?",
        ["Último disponível", "Data específica"],
        label_visibility="collapsed",
    )

    selected_date_str: str | None = None
    if mode == "Data específica":
        picked = st.sidebar.date_input(
            "Escolha uma data",
            value=date.today(),
            max_value=date.today(),
        )
        selected_date_str = picked.isoformat()

    st.sidebar.divider()
    st.sidebar.header("Filtros")

    # Sector filter (uses whatever sectors exist in the current briefing)
    if latest_briefing and latest_briefing.get("results"):
        sectors = sorted(
            {r["ticker"]["sector"] or "Sem setor" for r in latest_briefing["results"]}
        )
        selected_sectors = st.sidebar.multiselect(
            "Setores",
            sectors,
            default=sectors,
        )
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
        "AlphaGen Daily · "
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


def render_ticker_card(result: dict[str, Any]) -> None:
    """Render one ticker card with expandable chart."""
    ticker = result["ticker"]
    symbol = ticker["symbol"]

    with st.container(border=True):
        # Header row: symbol + company + price
        col_left, col_right = st.columns([3, 1])
        with col_left:
            st.subheader(symbol)
            company = ticker["company_name"]
            sector = ticker["sector"] or "Sem setor"
            industry = ticker.get("industry") or ""
            caption = f"{company} · {sector}"
            if industry:
                caption += f" · {industry}"
            st.caption(caption)
        with col_right:
            st.metric("Preço", f"${ticker['current_price']:.2f}")

        # Metrics row
        col_qoq, col_yoy, col_pe, col_mcap = st.columns(4)
        col_qoq.metric(
            "EPS Q/Q",
            f"{ticker.get('eps_growth_qoq') or 0:+.1f}%",
        )
        col_yoy.metric(
            "EPS Y/Y",
            f"{ticker.get('eps_growth_yoy') or 0:+.1f}%",
        )
        pe = ticker.get("pe_ratio")
        col_pe.metric("P/E", f"{pe:.1f}" if pe else "N/A")

        mcap = ticker.get("market_cap")
        if mcap:
            mcap_str = f"${mcap / 1e9:.1f}B" if mcap >= 1e9 else f"${mcap / 1e6:.0f}M"
        else:
            mcap_str = "N/A"
        col_mcap.metric("Market Cap", mcap_str)

        # Thesis + Risk
        st.markdown(f"**Tese:** {result['thesis']}")
        st.markdown(f"**Risco chave:** {result['key_risk']}")

        # SMA chart on demand
        with st.expander("📈 Ver preço e médias móveis (últimos 180 dias)"):
            with st.spinner(f"Baixando histórico de {symbol}..."):
                df = fetch_price_history(symbol, days=240)

            if df is None or df.empty:
                st.warning("Histórico de preços não disponível para este ticker.")
            else:
                fig = build_price_sma_chart(df, symbol)
                st.plotly_chart(fig, use_container_width=True)

                # Small text explaining what to look at
                st.caption(
                    "SMA20 > SMA50 > SMA200 é o critério de uptrend do screening. "
                    "Preço acima das três indica momento técnico forte."
                )


# ---------- Main ----------


def main() -> None:
    """Entry point — renders the whole page."""
    # Fetch briefing based on sidebar selection
    # We render the sidebar first (with None) just to know the selected date,
    # then fetch, then render the sidebar again with the briefing data for the
    # sector filter. Streamlit reruns the whole script on interactions, so this
    # two-pass approach ends up with a consistent UI.
    with st.spinner("Carregando último briefing..."):
        preliminary = fetch_briefing(target_date=None)

    selected_date, selected_sectors, selected_sort = render_sidebar(preliminary)

    briefing = preliminary if selected_date is None else fetch_briefing(selected_date)

    if briefing is None:
        st.error(
            f"Nenhum briefing encontrado{'  para ' + selected_date if selected_date else ''}. "
            "O screener roda em dias úteis às 09:00 BRT — pode ser cedo demais hoje, "
            "ou a data escolhida está fora do histórico."
        )
        return

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
        f"{len(filtered)} ticker(s) aprovado(s)"
        + (f" — filtrado de {len(all_results)}" if len(filtered) < len(all_results) else "")
    )

    for result in filtered:
        render_ticker_card(result)


if __name__ == "__main__":
    main()
