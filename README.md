# KnoweTrade

KnoweTrade is a monorepo scaffold for a long-only, low-frequency ETF trading platform.

## Architecture

- `apps/web`: React + TypeScript dashboard (Netlify-hosted)
- `apps/api`: FastAPI admin/read API (Render web service)
- `apps/worker`: Python strategy + execution worker (Render worker/cron)
- `packages/core`: shared strategy and risk logic
- `packages/broker-alpaca`: required scaffold folder for Alpaca integration assets
- `packages/broker_alpaca`: Python Alpaca adapter module used by worker
- `packages/db`: SQLAlchemy models and DB helpers
- `packages/alerts`: Slack alert helper
- `supabase`: migrations and seed SQL for Postgres
- `infra`: Render and Netlify deployment scaffolds

### Guardrails

- Frontend must never call broker APIs directly.
- Broker calls happen in worker/backend only.
- API reads from DB and exposes admin endpoints.
- v1 assumptions: long-only, low-frequency, ETF-based execution.
- Keep changes auditable: orders, fills, positions, risk events, and job runs.

## Database tables included

- `symbols`
- `signals`
- `orders`
- `fills`
- `positions`
- `portfolio_snapshots`
- `risk_events`
- `job_runs`

## Local setup

1. Copy environment template:

   - PowerShell: `Copy-Item .env.example .env`
   - Bash: `cp .env.example .env`

2. Create Python virtual environment and install backend deps:

   - `python -m venv .venv`
   - PowerShell: `.venv\Scripts\Activate.ps1`
   - `pip install -r requirements.txt`

3. Install frontend dependencies:

   - `npm install`

4. Run API (from repo root):

   - PowerShell: `$env:PYTHONPATH='.'; uvicorn apps.api.main:app --reload --port 8000`
   - Bash: `PYTHONPATH=. uvicorn apps.api.main:app --reload --port 8000`
   - Or: `npm run dev:api`

5. Run worker (from repo root):

   - PowerShell: `$env:PYTHONPATH='.'; python -m apps.worker.main`
   - Bash: `PYTHONPATH=. python -m apps.worker.main`
   - Or: `npm run dev:worker`

6. Run frontend:

   - `npm run dev:web`

7. Run tests (optional scaffold):

   - `pip install -r requirements-dev.txt`
   - PowerShell: `$env:PYTHONPATH='.'; pytest`
   - Bash: `PYTHONPATH=. pytest`

### Manifests

- Root Node workspace manifest: `package.json`
- Frontend manifest: `apps/web/package.json`
- Backend manifests: `apps/api/pyproject.toml`, `apps/worker/pyproject.toml`
- Backend dependency files: `apps/api/requirements.txt`, `apps/worker/requirements.txt`, `requirements.txt`

## Deploy overview

- Render blueprint scaffold: `infra/render.yaml`
  - `knowetrade-api` web service
  - `knowetrade-worker` background worker
  - `knowetrade-reconcile` cron scaffold
- Netlify config scaffold: `infra/netlify.toml`
- Supabase schema migration: `supabase/migrations/0001_initial_schema.sql`
