# 🗺️ AlphaGen Daily — Mapa de Evolução

> O que fazer com o JSON gerado pelo pipeline serverless da AlphaGen Daily.
> Organizado em 7 níveis por complexidade, com esforço estimado, custo e público-alvo.

---

## Índice

1. [Nível 1 — Consumo direto do endpoint](#nível-1--consumo-direto-do-endpoint)
2. [Nível 2 — Camada de notificação](#nível-2--camada-de-notificação)
3. [Nível 3 — Camada visual (dashboards e sites)](#nível-3--camada-visual-dashboards-e-sites)
4. [Nível 4 — Persistência avançada (histórico + queries)](#nível-4--persistência-avançada-histórico--queries)
5. [Nível 5 — Enriquecimento (mais inteligência)](#nível-5--enriquecimento-mais-inteligência)
6. [Nível 6 — Comercialização (virar produto)](#nível-6--comercialização-virar-produto)
7. [Nível 7 — Escala e robustez](#nível-7--escala-e-robustez)
8. [🎯 Roadmap sugerido](#-roadmap-sugerido)
9. [💡 Perguntas estratégicas](#-perguntas-estratégicas-para-guiar-a-decisão)

---

## Nível 1 — Consumo direto do endpoint

O JSON está no ar. Qualquer pessoa ou aplicação com acesso à URL pode consumir sem intermediário.

### 1.1 Via terminal (curl / wget / httpie)

Para você mesmo. Roda `curl` e vê. Zero infraestrutura adicional. Ideal para debug rápido.

### 1.2 Via navegador (Chrome + extensão JSON Viewer)

Público leigo. Só compartilha a URL. Pessoas sem programação abrem e leem.

### 1.3 Via script Python local (uso pessoal automatizado)

Você roda `python meu_script.py` toda manhã. Ele faz o fetch, filtra por setor que te interessa e imprime formatado.

| Atributo | Valor |
|---|---|
| Complexidade | Baixa |
| Tempo de setup | ~30 min |
| Custo | Zero |

Exemplo esquelético:

```python
import requests

url = "https://r0kn41v28a.execute-api.us-east-1.amazonaws.com/today"
data = requests.get(url).json()

for r in data["results"]:
    if r["ticker"]["sector"] == "Technology":
        print(f"{r['ticker']['symbol']}: {r['thesis']}")
```

---

## Nível 2 — Camada de notificação

Aqui o dado vai atrás de você em vez de você ir atrás do dado. Todas as opções são orquestráveis dentro do próprio Lambda existente (basta adicionar mais um passo no fim do pipeline).

### 2.1 E-mail diário via Amazon SES ✅ CONCLUÍDO

| Atributo | Valor |
|---|---|
| Complexidade | Baixa |
| Tempo | 2-3 h |
| Custo | Grátis até 62 mil e-mails/mês (Free Tier) |
| Para quem | Você e amigos investidores. Formato "newsletter matinal pessoal" |

**Status:** implementado em `src/notifier.py`, wired no `handler.py` como step 6 do pipeline. HTML rich + plain text fallback, envio via Amazon SES. Config via env vars `NOTIFY_ENABLED`, `SES_SENDER`, `SES_RECIPIENTS`.

Gotcha encontrado: domínios como yahoo.com, gmail.com e outros grandes publicam DMARC estrito (`p=reject`) que bloqueia envio via SES sem verificação de domínio. Solução usada: sender em domínio com DMARC permissivo (`p=quarantine`). Solução robusta futura: registrar domínio próprio e configurar DKIM.

### 2.2 Telegram bot

| Atributo | Valor |
|---|---|
| Complexidade | Baixa |
| Tempo | 2 h |
| Custo | Zero |
| Para quem | Você no celular, grupo fechado de amigos |

Cria o bot com **@BotFather** (5 min), pega o token e adiciona chamada HTTP para a API do Telegram no fim do pipeline mandando texto formatado. Notificação chega como qualquer outra mensagem.

### 2.3 Slack / Discord webhook

| Atributo | Valor |
|---|---|
| Complexidade | Baixa |
| Tempo | 1 h |
| Custo | Zero |
| Para quem | Times de trabalho, comunidades de investimento |

Slack te dá webhook URL, você faz `POST` com o payload formatado. Discord idem.

### 2.4 WhatsApp via Twilio API

| Atributo | Valor |
|---|---|
| Complexidade | Média |
| Tempo | 4-6 h |
| Custo | ~$0.005 por mensagem (Twilio) |
| Para quem | Você mesmo ou lista pequena de assinantes |

Conta Twilio, número WhatsApp Business API, template aprovado pela Meta, chamada HTTP no pipeline.

### 2.5 Push mobile via Firebase

| Atributo | Valor |
|---|---|
| Complexidade | Média |
| Tempo | 6-8 h |
| Custo | Zero até volumes altos |
| Para quem | Produto próprio com app mobile |

App mobile registra device token no seu backend. Lambda dispara para Firebase Cloud Messaging que entrega push.

---

## Nível 3 — Camada visual (dashboards e sites)

Transforma o JSON cru em interface bonita, navegável, compartilhável.

### 3.1 Streamlit — MVP visual em 1 dia

| Atributo | Valor |
|---|---|
| Complexidade | Baixa |
| Tempo | 4-8 h |
| Custo | Zero (Streamlit Cloud) ou baixo (EC2 t3.micro) |
| Para quem | Primeira interface visual. Perfeito para portfólio |

Script Python de ~200 linhas que faz fetch do endpoint e renderiza tabela + gráficos com Plotly. Deploy num clique no Streamlit Cloud.

Exemplo esquelético:

```python
import streamlit as st
import requests

url = "https://r0kn41v28a.execute-api.us-east-1.amazonaws.com/today"
data = requests.get(url).json()

st.title("AlphaGen Daily")
st.metric("Ações aprovadas hoje", data["approved_count"])

for r in data["results"]:
    with st.expander(f"{r['ticker']['symbol']} — {r['ticker']['company_name']}"):
        st.write(f"**Tese:** {r['thesis']}")
        st.write(f"**Risco:** {r['key_risk']}")
        st.metric("EPS Y/Y", f"{r['ticker']['eps_growth_yoy']:.1f}%")
```

### 3.2 Site estático (HTML/CSS/JS puro)

| Atributo | Valor |
|---|---|
| Complexidade | Baixa |
| Tempo | 8-16 h |
| Custo | Grátis (S3 + CloudFront, Netlify ou Vercel) |
| Para quem | Landing page profissional do projeto no portfólio |

Página HTML que faz `fetch()` no endpoint e renderiza cards. Zero backend adicional.

### 3.3 Next.js / React app profissional

| Atributo | Valor |
|---|---|
| Complexidade | Média |
| Tempo | 20-40 h |
| Custo | Grátis (Vercel Free Tier) |
| Para quem | Produto sério que você pretende evoluir. Pode virar SaaS |

Projeto React/Next.js completo com home, página histórica, filtros por setor, gráficos com Recharts ou widget TradingView.

### 3.4 Astro (static site com dados dinâmicos no build)

| Atributo | Valor |
|---|---|
| Complexidade | Média |
| Tempo | 12-20 h |
| Custo | Grátis |
| Para quem | Melhor combinação de SEO + performance para produto público |

Astro faz build estático mas consome APIs no build. Regenera 1x/dia via GitHub Actions ou cron do Vercel. Super rápido, sem servidor.

### 3.5 Grafana dashboard

| Atributo | Valor |
|---|---|
| Complexidade | Média-alta |
| Tempo | 8-16 h |
| Custo | Grátis (Grafana Cloud Free Tier) |
| Para quem | Análise interna, ops-style |

Conecta ao S3 ou DynamoDB via plugin. Dashboard com séries temporais dos tickers aprovados, contagem por setor, evolução de share. Menos "bonito" que Streamlit, mais expressivo.

### 3.6 Metabase / Apache Superset

| Atributo | Valor |
|---|---|
| Complexidade | Média |
| Tempo | 12-20 h |
| Custo | Baixo (EC2 t3.small ou Fargate) |
| Para quem | Explorar dados sem código, filtros, cortes por setor/data |

Deploy do Metabase conectado a um Postgres alimentado por Lambda. Dashboards drag-and-drop.

### 3.7 Power BI

| Atributo | Valor |
|---|---|
| Complexidade | Baixa |
| Tempo | 4-8 h |
| Custo | Grátis para uso pessoal, ~R$ 55/mês licença Pro |
| Para quem | Você já domina Power BI (UrbanIQ). Uso pessoal ou apresentação |

Power BI conecta direto ao endpoint via "Web Source". Refresh diário automático. Dashboard corporativo bonito em horas.

### 3.8 Looker Studio (Google)

| Atributo | Valor |
|---|---|
| Complexidade | Baixa |
| Tempo | 4-6 h |
| Custo | Grátis |
| Para quem | Compartilhamento fácil via link Google |

Conector customizado ou intermediário via Google Sheets (Apps Script consome JSON e escreve na planilha, Looker consome a planilha).

---

## Nível 4 — Persistência avançada (histórico + queries)

Hoje o JSON é sobrescrito diariamente (só `latest.json` + arquivos dated). Para consultar histórico com SQL, agregar por semana/mês e comparar performance ao longo do tempo, você precisa de estrutura de dados relacional.

### 4.1 Amazon RDS PostgreSQL

| Atributo | Valor |
|---|---|
| Complexidade | Média |
| Tempo | 10-15 h |
| Custo | ~$15/mês (db.t3.micro) |
| Para quem | Análises históricas sérias, base para dashboards |

Cria tabela `screening_history` com colunas (data, symbol, price, eps_qoq, thesis, etc). Adiciona ETL no Lambda que insere cada execução.

Exemplo de query:

```sql
-- Tickers que apareceram nos últimos 30 dias, ordenados por frequência
SELECT symbol, COUNT(*) AS vezes_aprovado
FROM screening_history
WHERE run_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY symbol
ORDER BY vezes_aprovado DESC;
```

Isso vira insight que o JSON puro não te dá.

### 4.2 Amazon Athena + S3 (data lake serverless)

| Atributo | Valor |
|---|---|
| Complexidade | Média-alta |
| Tempo | 12-20 h |
| Custo | ~$5/TB escaneado (muito barato para volumes pequenos) |
| Para quem | Serverless puro, sem servidor de banco. Ideal para volumes crescentes |

Os arquivos JSON dated que você já salva no S3 viram particionamento natural. Cria tabela Athena apontando para o S3 e roda SQL direto nos arquivos.

### 4.3 Amazon Redshift ou Snowflake (data warehouse)

| Atributo | Valor |
|---|---|
| Complexidade | Alta |
| Tempo | 40+ h |
| Custo | Significativo ($100+/mês) |
| Para quem | Produto grande com milhares de tickers e anos de histórico. Overkill para MVP |

ETL pesado, star schema, agregações pré-calculadas.

### 4.4 Parquet files no S3 (analytics-friendly)

| Atributo | Valor |
|---|---|
| Complexidade | Média |
| Tempo | 6-10 h |
| Custo | Só S3 (fração de centavo) |
| Para quem | Analytics rápido em Python/notebook |

Em vez de só JSON, salva também versão Parquet (colunar). Pronto para pandas, Spark, Athena e Databricks.

### 4.5 Enriquecer o DynamoDB atual

| Atributo | Valor |
|---|---|
| Complexidade | Baixa |
| Tempo | 2-4 h |
| Custo | Dentro do Free Tier |
| Para quem | Histórico simples, sem sair da AWS existente |

Adiciona GSI (Global Secondary Index) por symbol e por sector. Habilita queries do tipo "todos os dias em que NVDA foi aprovada".

---

## Nível 5 — Enriquecimento (mais inteligência)

Hoje o JSON tem screener + tese. Você pode expandir com análises complementares.

### 5.1 Análise de sentimento de notícias

| Atributo | Valor |
|---|---|
| Complexidade | Média |
| Tempo | 15-25 h |
| Custo | ~$5-15/mês (NewsAPI ou Alpha Vantage) |
| Para quem | Ver se o ticker está "quente" ou "frio" na mídia além do técnico |

Para cada ticker aprovado, busca headlines das últimas 24 h. Passa por Bedrock (ou Comprehend) para gerar sentimento agregado. Adiciona ao JSON.

### 5.2 Indicadores técnicos adicionais

| Atributo | Valor |
|---|---|
| Complexidade | Baixa |
| Tempo | 4-8 h |
| Custo | Zero (só CPU do Lambda) |
| Para quem | Screener técnico mais rico. Nível analista real |

Biblioteca `ta` (Python) calcula RSI, MACD, Bollinger Bands, Stochastic. Adiciona ao objeto ticker.

### 5.3 Backtesting histórico

| Atributo | Valor |
|---|---|
| Complexidade | Alta |
| Tempo | 40-60 h |
| Custo | Baixo (batch em Lambda ou EC2 spot) |
| Para quem | Validar cientificamente a estratégia antes de expor como produto |

Roda o screener retroativamente para os últimos 2-3 anos, simula compra dos tickers aprovados e mede performance. Descobre se a estratégia funciona na prática.

### 5.4 Correlação e diversificação

| Atributo | Valor |
|---|---|
| Complexidade | Média |
| Tempo | 10-15 h |
| Para quem | Investidor que quer aprovar 5 mas não quer 5 semicondutoras |

Para os N tickers aprovados, calcula matriz de correlação de preços últimos 90 dias. Sugere subset diversificado.

### 5.5 Simulação de portfólio

| Atributo | Valor |
|---|---|
| Complexidade | Média |
| Tempo | 15-20 h |
| Para quem | Validar visualmente se o screener superou o mercado |

Dado o histórico de aprovados, monta portfólio hipotético equal-weight e mostra performance vs S&P 500.

---

## Nível 6 — Comercialização (virar produto)

Aqui você começa a pensar em usuários pagantes.

### 6.1 Landing page + trial gratuito

| Atributo | Valor |
|---|---|
| Complexidade | Média |
| Tempo | 30-50 h |
| Custo | ~$20/mês (Vercel + domínio) |
| Para quem | Testar market fit |

Site em Next.js explicando o produto. Cadastro (Cognito ou Supabase), trial de 14 dias, cobrança via Stripe.

### 6.2 API pública paga (freemium)

| Atributo | Valor |
|---|---|
| Complexidade | Média-alta |
| Tempo | 20-40 h |
| Custo | API Gateway cobra por request, você cobra mais |
| Para quem | Desenvolvedores que querem consumir seu screener |

Autenticação via API keys, rate limit por plano (free = 10 requests/dia, pago = ilimitado), billing via Stripe.

### 6.3 Assinatura de conteúdo (newsletter paga)

| Atributo | Valor |
|---|---|
| Complexidade | Média |
| Tempo | 20-30 h |
| Custo | Substack (grátis) ou ConvertKit (~$15/mês) |
| Para quem | Monetização direta sem complexidade técnica |

O próprio JSON alimenta uma newsletter diária. Monetiza via assinatura (Substack cobra 10% do que você fatura).

### 6.4 App mobile próprio (React Native / Flutter)

| Atributo | Valor |
|---|---|
| Complexidade | Alta |
| Tempo | 100+ h |
| Custo | App Store $99/ano + Google Play $25 vitalício |
| Para quem | Produto sério com base de usuários mobile-first |

App que consome sua API. Briefing formatado bonito, push notification.

### 6.5 Marketplace (plugin para plataformas de trading)

| Atributo | Valor |
|---|---|
| Complexidade | Alta |
| Tempo | Varia muito |
| Para quem | Vertical bem definido de traders profissionais |

Vende o screener como plugin para TradingView, MetaTrader ou plataformas nichadas.

---

## Nível 7 — Escala e robustez

Quando o produto crescer, essas coisas viram necessárias.

- **Multi-região** — deploy em `us-west-2` e `sa-east-1` (São Paulo) para redundância.
- **CloudFront CDN + WAF** — CloudFront na frente do API Gateway para cache. WAF filtra ataques.
- **Autenticação (Amazon Cognito)** — user pools com login social (Google, GitHub).
- **Rate limiting sofisticado** — API Gateway usage plans, throttling por API key, limite por plano.
- **Observabilidade avançada** — Datadog, New Relic ou X-Ray para tracing distribuído. Alarmes CloudWatch para SLA.
- **CI/CD pipeline** — GitHub Actions ou CodePipeline rodando testes + deploy automático a cada push.
- **Testes automatizados** — unit tests com pytest, integration com moto (mock AWS), end-to-end periódicos.

---

## 🎯 Roadmap sugerido

Considerando perfil de transição de carreira, portfolio building e aprendizado técnico, a ordem que maximiza valor:

### Fase 1 — Próximas 2 semanas (5-10 h)

- [x] Adicionar **e-mail diário via SES** ao pipeline (baixa complexidade, útil de imediato)
- [ ] Criar **Streamlit app** consumindo o endpoint (portfolio visual pronto)
- [ ] Adicionar **RSI + MACD** ao ticker (enriquece com indicadores clássicos)

### Fase 2 — Próximo mês (20-30 h)

- [ ] Migrar histórico para **Athena + S3 parquet** (habilita análises longas)
- [ ] Publicar **Next.js site** com home + histórico + filtros (portfolio profissional)
- [ ] Adicionar **Telegram bot** (produto real usável no dia a dia)

### Fase 3 — Próximos 3 meses (50-80 h)

- [ ] Adicionar **análise de sentimento de notícias** (diferencial competitivo)
- [ ] Implementar **backtesting histórico** (valida estratégia)
- [ ] Adicionar **mercado brasileiro (B3)** (nicho único, você pode virar referência)

### Fase 4 — Quando fizer sentido (100+ h)

- [ ] Landing page profissional
- [ ] Trial pago via Stripe
- [ ] Autenticação e rate limiting

---

## 💡 Perguntas estratégicas para guiar a decisão

Antes de escolher para onde ir, três perguntas orientam mais do que qualquer feature específica.

### Pergunta 1 — Para quem é o produto no fim?

| Público | Foco recomendado |
|---|---|
| Você mesmo (uso pessoal) | Notificações + Streamlit |
| Amigos investidores | Telegram / WhatsApp / e-mail |
| Comunidade pública ampla | Site profissional + SEO |
| Desenvolvedores | API pública |

### Pergunta 2 — Seu objetivo com o projeto?

| Objetivo | Foco recomendado |
|---|---|
| Portfolio para conseguir emprego | Streamlit + site Next.js (vitrine perfeita) |
| Aprender cada tecnologia AWS/dados | Adiciona uma camada por mês |
| Virar produto que gera renda | Funil de aquisição + monetização |

### Pergunta 3 — Quanto tempo por semana?

| Disponibilidade | Foco recomendado |
|---|---|
| 2-3 h | Coisas pequenas (notificação, indicador extra) |
| 5-10 h | Dashboard visual + persistência |
| 15+ h | Produto completo com frontend próprio |

---

## 🎬 Encerramento

O JSON que sai do endpoint hoje é **matéria-prima**. Cada nível deste mapa é uma refinaria diferente que transforma essa matéria-prima em algo útil de forma distinta.

Não precisa (nem deve) construir tudo. Escolhe 2-3 caminhos que mais te empolgam, executa, publica, escreve sobre cada um.

Cada camada adicionada é:

- 1 novo tópico para o CV
- 1 nova skill técnica dominada
- 1 novo item no portfólio GitHub
- Potencialmente 1 novo artigo técnico

**Marca este mapa e volta a ele quando precisar decidir o próximo passo.** Você já construiu a fundação sobre a qual todas essas coisas podem se erguer.
