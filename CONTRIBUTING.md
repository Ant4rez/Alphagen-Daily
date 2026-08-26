# Contribuindo para o AlphaGen Daily

Este projeto é mantido por uma pessoa só hoje, então este documento é primariamente um contrato do desenvolvedor com o próprio projeto: um lembrete escrito das regras que evitam retrabalho ou perda de contexto ao longo do tempo. Se algum dia alguém externo quiser contribuir, este arquivo já orienta o fluxo.

## Ambiente local

```bash
git clone https://github.com/Ant4rez/Alphagen-Daily.git
cd Alphagen-Daily

python -m venv .venv
source .venv/bin/activate           # Linux/Mac
# .venv\Scripts\activate            # Windows

pip install -r requirements.txt -r requirements-dev.txt
```

Docker Desktop precisa estar instalado e rodando para `sam build --use-container`. AWS CLI e AWS SAM CLI configurados para deploy.

## Fluxo de trabalho

Um branch por mudança, um propósito por branch. Nada direto na `main`.

```bash
git checkout -b feat/rsi-macd
# edita, testa, commita
git push -u origin feat/rsi-macd
# abre PR (mesmo sendo você mesmo o reviewer, o histórico de PR ajuda a documentar a mudança)
```

## Antes de abrir um PR

Rodar localmente:

```bash
make lint      # ruff check + mypy
make test      # pytest
```

Se `make lint` reportar problemas, `make format` corrige a maioria automaticamente.

## Regra de documentação

Mudanças que afetam o comportamento do sistema **exigem** atualização de documentação no mesmo PR:

| O que mudou | Documento a atualizar |
|---|---|
| Novo serviço AWS no stack | `CONTEXT.md` seção 3, `ARCHITECTURE.md` seção 9 |
| Novo threshold ou env var | `CONTEXT.md` seção 6, `ARCHITECTURE.md` seção 8 |
| Novo módulo em `src/` | `ARCHITECTURE.md` seção 5 |
| Mudança de esquema de storage | `ARCHITECTURE.md` seção 7 |
| Novo endpoint HTTP | `ARCHITECTURE.md` seção 4 |
| Gotcha descoberto | `CONTEXT.md` seção 7 |
| Item do roadmap concluído | `alphagen_daily_roadmap.md` + `CONTEXT.md` seção 9 |

Alterações puramente cosméticas (refatoração de nome de variável, formatação, correção de typo em comentário) não exigem update de docs.

## Convenções de commit

Padrão [Conventional Commits](https://www.conventionalcommits.org):

| Prefixo | Uso |
|---|---|
| `feat:` | Nova funcionalidade visível |
| `fix:` | Correção de bug |
| `refactor:` | Reorganização sem mudança de comportamento |
| `chore:` | Manutenção (deps, config, gitignore) |
| `docs:` | Só documentação |
| `test:` | Só testes |
| `ci:` | Só pipeline de CI/CD |
| `perf:` | Otimização mensurável |

Mensagens no imperativo, em inglês, primeira linha até 72 caracteres. Corpo opcional explicando o "por quê" quando não for óbvio pelo diff.

Exemplos:

```
feat: add RSI and MACD indicators to Ticker snapshot
fix: handle empty S3 response in api_handler /today route
refactor: extract Bedrock client creation from analyze_batch
chore: bump yfinance to 0.2.68
docs: sanitize CONTEXT.md for public repo
```

## O que não commitar

Arquivos e diretórios em `.gitignore` são bloqueados por design. Alguns lembretes:

- **Credenciais AWS ou tokens** de qualquer serviço. Nunca, em hipótese alguma.
- **Arquivos `.env`** com valores reais. Um `.env.example` com placeholders pode ser commitado se ajudar novos colaboradores.
- **Outputs de invocação local** (`response.json`, `infrastructure/response.json`).
- **Artefatos de build** (`.aws-sam/`, `dist/`, `build/`).
- **Caches** (`__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`).
- **Ambientes virtuais** (`.venv/`, `venv/`, `env/`).
- **Configuração local do SAM** (`samconfig.toml.local`) — o `samconfig.toml` compartilhado fica no repo.

Se por acidente commitar algo que não deveria, além de rodar `git rm --cached`, considere se o conteúdo era sensível (credencial, chave). Nesse caso, rotacione o segredo imediatamente e considere reescrever o histórico com `git filter-repo`.

## Ao adicionar um ticker ao universo

O universo vive em `src/universe/ai_tickers.py`, organizado por vertical. Ao adicionar:

1. Escolher a vertical mais adequada (não criar vertical nova sem pelo menos 3 tickers)
2. Manter alfabético dentro da vertical? Não é obrigatório, mas ajuda revisão
3. Comentário curto ao lado do símbolo explicando o vínculo com IA
4. Rebuild + deploy: `cd infrastructure && sam build --use-container && sam deploy`

## Ao mexer em threshold

Thresholds vivem no `template.yaml` sob `Globals.Function.Environment.Variables`. Não precisa rebuild da imagem, só `sam deploy`. Registrar no PR **por que** o novo valor faz sentido (o valor anterior estava filtrando demais ou de menos?).

## Testes

Hoje `tests/` está com esqueletos vazios. Prioridade quando escrever os primeiros testes:

1. `screener.py` — lógica pura, fácil de cobrir, alto valor
2. `_parse_llm_response` em `analyzer.py` — função defensiva, precisa ser à prova de balas
3. `storage._to_dynamodb_safe` — conversão recursiva de tipos, fácil de testar unitário
4. Handlers com mock via `moto` (biblioteca já está em `requirements-dev.txt`)

Meta razoável para o começo: 60% de cobertura em `src/`, verificado por `pytest --cov=src`.

## Reviewers

Enquanto o projeto é single-maintainer, o próprio autor é o reviewer. Regra: só faz merge depois de dormir uma noite sobre mudanças grandes (mais de 100 linhas de código produção). Isso pega bugs bobos que a mente cansada normaliza.
