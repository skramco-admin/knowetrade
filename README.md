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

## ETF universe and monitoring

- ETF universe is stored in the `symbols` table.
- Worker monitors only symbols where:
  - `is_active = true`
  - `asset_class = 'ETF'`
  - `strategy_bucket = 'etf_trend'`
- Worker logs include:
  - symbol load success
  - active ETF count
  - exact monitored tickers

### Manage ETFs

- Add an ETF:
  - insert a row into `symbols` with `ticker`, `asset_class='ETF'`, `strategy_bucket='etf_trend'`, `is_active=true`
- Disable an ETF without deleting history:
  - set `is_active=false` for that ticker
- Move an ETF out of v1 monitoring:
  - change `strategy_bucket` to another value

Seed and migrations for the v1 universe are in:

- `supabase/migrations/0002_symbols_universe_columns.sql`
- `supabase/seed.sql`

## Daily paper trading workflow

Production-style daily workflow uses separate callable worker jobs:

- `premarket_health_check`
- `etf_data_ingestion`
- `etf_signal_generation`
- `dry_run_portfolio_decisioning`
- `paper_order_execution`
- `daily_reconciliation`
- `daily_summary`

Render cron wiring is defined in `infra/render.yaml`.

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

8. Keep trading disabled during monitoring setup:

   - `TRADING_ENABLED=false`
   - `DRY_RUN=true`

## Required environment flags

- `APP_ENV` (e.g. `production`)
- `APP_MODE` (`paper` only in v1)
- `TRADING_ENABLED` (`false` disables all order submission)
- `ENABLE_ORDER_SUBMISSION` (`false` by default; must be `true` to submit)
- `ALPACA_API_KEY`
- `ALPACA_API_SECRET` or `ALPACA_SECRET_KEY`
- `ALPACA_BASE_URL` (`https://paper-api.alpaca.markets`)
- `ALPACA_DATA_BASE_URL` (`https://data.alpaca.markets`)
- `SLACK_WEBHOOK_URL`
- `DATABASE_URL`
- `MAX_OPEN_POSITIONS` (default `5`)
- `MAX_POSITION_PCT` (default `0.20`)
- `LOG_LEVEL`

## Safety controls

- Order submission is blocked unless all are true:
  - `APP_MODE=paper`
  - `TRADING_ENABLED=true`
  - `ENABLE_ORDER_SUBMISSION=true` (or admin setting enabled)
- Hard paper-only guard blocks non-paper Alpaca order endpoint.
- Kill switch: set `TRADING_ENABLED=false` to instantly disable submissions.
- Admin toggles:
  - `POST /admin/paper-trading/enable`
  - `POST /admin/paper-trading/disable`

## Daily cron jobs

- Premarket check: `run_premarket_health_check_job`
- Post-close chain (ingest + signals + decisioning): `run_postclose_workflow_job`
- Order submission window: `run_paper_order_execution_job`
- Reconciliation: `run_reconciliation_job`
- Daily summary: `run_daily_summary_job`

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
- Symbols metadata migration: `supabase/migrations/0002_symbols_universe_columns.sql`
- Price bars migration: `supabase/migrations/0003_price_bars_table.sql`
- Signals extension migration: `supabase/migrations/0004_signals_reason.sql`
- Proposed orders migration: `supabase/migrations/0005_proposed_orders.sql`
- Orders/fills alignment migration: `supabase/migrations/0006_orders_and_fills_alignment.sql`
- Audit logs migration: `supabase/migrations/0007_audit_logs.sql`
