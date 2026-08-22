# AlphaGen Daily

> Always-on AWS agent that screens AI-related US stocks using CANSLIM-inspired criteria and generates daily analytical briefings powered by Amazon Bedrock (Nova Lite).

Built for the **AWS Weekend Creative Agent Challenge** (August 2026).

## Overview

AlphaGen Daily runs autonomously every trading day. Before US market opens, it:

1. Downloads price history and fundamentals for a curated universe of ~70 AI-related tickers (semiconductors, hyperscalers, enterprise AI SaaS, cloud data platforms, AI infrastructure)
2. Applies CANSLIM-inspired filters (EPS growth Q/Q > 15%, Y/Y > 25%, price momentum via SMA crossovers)
3. Uses Amazon Bedrock (Nova Lite) to generate a concise analytical narrative for each approved ticker
4. Persists the daily briefing to S3 and DynamoDB
5. Exposes results via a public HTTP endpoint

No manual steps. No console. Ready when you return.

## Architecture

Refer to [ARCHITECTURE.md](ARCHITECTURE.md) for full details.

### AWS Services Used

- **Amazon EventBridge Scheduler** — cron trigger (weekdays, pre-market)
- **AWS Lambda** — orchestration and processing
- **Amazon Bedrock (Nova Lite)** — LLM-based analysis
- **Amazon S3** — daily briefing storage
- **Amazon DynamoDB** — execution history (last 60 runs)
- **Amazon API Gateway (HTTP)** — public endpoints (`/today`, `/history/{date}`)
- **Amazon CloudWatch Logs** — observability
- **AWS Systems Manager Parameter Store** — configuration
- **AWS SAM** — infrastructure as code

## Getting Started

### Prerequisites

- Python 3.11
- AWS CLI configured
- AWS SAM CLI installed
- Amazon Bedrock model access enabled for Nova Lite

### Local Setup

\`\`\`bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt -r requirements-dev.txt
\`\`\`

### Run Tests

\`\`\`bash
make test
\`\`\`

### Deploy

\`\`\`bash
make deploy
\`\`\`

## Roadmap

- [ ] Add Brazilian market (B3) support with adjusted CANSLIM thresholds
- [ ] Add sentiment layer from news headlines
- [ ] Add Slack/email delivery via Amazon SNS
- [ ] Add multi-strategy screening (value, dividend, quality)
- [ ] Add backtest module for historical validation

## Author

Thiago Fiel de Oliveira — Data Science student at FIAP, AWS Certified AI Practitioner.

## License

MIT