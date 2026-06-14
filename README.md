# SmartShopAI

SmartShopAI is a secure, AWS-ready, multi-agent shopping assistant built with FastAPI,
Pydantic AI, GPT-4o-mini, Streamlit, Whisper speech-to-text, and SQL-backed product data.

## Agents

- Coordinator agent: routes customer questions and orchestrates specialist agents.
- Product recommendation agent: suggests products from catalog data.
- Review summarization agent: summarizes review sentiment and insights.
- Price comparison agent: compares product features and prices across brands.
- FAQ and policy agent: answers returns, refunds, shipping, and store policy questions.

The app uses read-only SQL tools with allowlisted tables and PII redaction. Conversation
context is ephemeral, redacted, and in-memory only; it is never written to the database.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python3 scripts/import_csv.py
uvicorn app.main:app --reload
```

In another terminal:

```bash
streamlit run streamlit_app.py
```

Set `OPENAI_API_KEY` in `.env` for GPT-4o-mini and Whisper. Without a key, the API uses
deterministic local fallbacks so tests and demos still work.

## CSV Import

Sample CSVs live in `data/`. Replace them with your own files using the same columns, then run:

```bash
python3 scripts/import_csv.py --products data/products.csv --reviews data/reviews.csv --policies data/policies.csv
```

For AWS RDS Postgres:

```bash
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@RDS_ENDPOINT:5432/smartshop python3 scripts/import_csv.py
```

## Docker

```bash
docker build -t smartshopai .
docker run --env-file .env -p 8000:8000 smartshopai
```

For Streamlit, run the app locally or build a second service image using the same package and:

```bash
streamlit run streamlit_app.py --server.port 8501
```

## Evaluation

```bash
python3 evals/run_evals.py
```

The eval script runs the dataset in `evals/agent_eval_dataset.jsonl` against `/chat` if the
API is running, or against the local orchestrator otherwise.

## AWS Notes

- Store secrets in AWS Secrets Manager or SSM Parameter Store.
- Use RDS Postgres with TLS and security groups scoped to the app runtime.
- Run the FastAPI image on ECS Fargate, App Runner, or EKS.
- Put API Gateway/ALB and WAF in front of the service.
- Keep `DATABASE_URL`, `OPENAI_API_KEY`, and CORS origins environment-specific.
