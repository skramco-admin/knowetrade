-- KnoweTrade v1 initial schema
-- Includes auditability tables for signals, orders, fills, positions, risk, and jobs.

create table if not exists symbols (
  id bigserial primary key,
  ticker text not null unique,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists signals (
  id bigserial primary key,
  symbol text not null,
  signal_type text not null,
  strength numeric(12,6) not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists orders (
  id bigserial primary key,
  broker_order_id text not null unique,
  symbol text not null,
  qty numeric(16,6) not null,
  side text not null check (side in ('buy', 'sell')),
  status text not null,
  created_at timestamptz not null default now()
);

create table if not exists fills (
  id bigserial primary key,
  order_id bigint not null references orders(id),
  fill_qty numeric(16,6) not null,
  fill_price numeric(16,6) not null,
  created_at timestamptz not null default now()
);

create table if not exists positions (
  id bigserial primary key,
  symbol text not null,
  qty numeric(16,6) not null default 0,
  avg_price numeric(16,6) not null default 0,
  updated_at timestamptz not null default now()
);

create table if not exists portfolio_snapshots (
  id bigserial primary key,
  equity numeric(16,6) not null,
  cash numeric(16,6) not null,
  created_at timestamptz not null default now()
);

create table if not exists risk_events (
  id bigserial primary key,
  symbol text not null,
  reason text not null,
  created_at timestamptz not null default now()
);

create table if not exists job_runs (
  id bigserial primary key,
  job_name text not null,
  status text not null,
  started_at timestamptz not null,
  finished_at timestamptz
);

create index if not exists idx_orders_symbol on orders(symbol);
create index if not exists idx_fills_order_id on fills(order_id);
create index if not exists idx_positions_symbol on positions(symbol);
create index if not exists idx_signals_symbol on signals(symbol);
create index if not exists idx_job_runs_job_name on job_runs(job_name);
