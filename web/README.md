# AlphaGen Daily — Web

Dashboard Streamlit que consome o endpoint público do AlphaGen Daily e renderiza o briefing diário com filtros e gráficos por ticker.

## Rodar local

Do diretório `web/`:

```bash
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows

pip install -r requirements.txt

streamlit run app.py
```

O app abre automaticamente em `http://localhost:8501`.

## Deploy no Streamlit Cloud

1. Faça login em [share.streamlit.io](https://share.streamlit.io) com sua conta GitHub
2. Clique em **Create app** → **Deploy a public app from GitHub**
3. Preencha:
   - **Repository**: `Ant4rez/Alphagen-Daily`
   - **Branch**: `main`
   - **Main file path**: `web/app.py`
   - **App URL**: escolha um subdomínio, ex: `alphagen-daily`
4. Clique **Deploy**

O Streamlit Cloud vai clonar o repo, instalar `web/requirements.txt` e servir o app em `https://alphagen-daily.streamlit.app`.

## Como o app funciona

- Faz `GET /today` no endpoint público para pegar o briefing mais recente
- Renderiza header, KPIs e um card por ticker aprovado
- Sidebar permite escolher data histórica (`GET /history/{YYYY-MM-DD}`), filtrar por setor e ordenar
- Ao expandir "Ver preço e médias móveis" num card, faz `yfinance.download` para os últimos ~240 dias e renderiza um chart Plotly com preço + SMA20/50/200
- Cache: briefing tem TTL de 5 minutos; histórico de preço, TTL de 1 hora

## Estrutura

```
web/
├── app.py              # Toda a aplicação em um arquivo
├── requirements.txt    # streamlit, requests, pandas, plotly, yfinance
├── .streamlit/
│   └── config.toml     # Tema e config do servidor
└── README.md
```

## Manutenção

Se você mudar thresholds no `template.yaml` do backend, atualize também a constante `DEPLOYED_THRESHOLDS` no topo de `app.py` para o painel de parâmetros mostrar os valores corretos.

Alternativa futura: expor os thresholds via endpoint `/config` no `api_handler.py` para eliminar a duplicação.
