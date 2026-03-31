# KnoweTrade Agent Instructions

You are building KnoweTrade, an automated trading platform with this architecture:

- Frontend: Netlify-hosted dashboard
- API: Render web service
- Worker: Render background worker
- Scheduled jobs: Render cron jobs
- Database: Supabase Postgres
- Alerts: Slack
- Broker v1: Alpaca
- Language: Python backend, TypeScript frontend

Core principles:
- Never let the frontend call the broker directly.
- All broker calls must go through backend services.
- Secrets must never be hardcoded.
- Use migrations for database changes.
- Prefer boring, reliable architecture over clever architecture.
- Keep v1 long-only, low-frequency, ETF-based.
- Build for auditability: orders, fills, positions, risk events, job runs.
- Use environment variables for all credentials.
- Default to small, testable files and clear comments.
