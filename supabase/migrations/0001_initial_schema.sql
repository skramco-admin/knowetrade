-- KnoweTrade v1 initial schema
-- Long-only, low-frequency ETF system with full auditability.

create table if not exists symbols (
  id bigserial primary key,
  ticker text not null unique,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists price_bars (
  id bigserial primary key,
  symbol text not null,
  timeframe text not null default '1d',
  bar_time timestamptz not null,
  open numeric(16,6) not null,
  high numeric(16,6) not null,
  low numeric(16,6) not null,
  close numeric(16,6) not null,
  volume bigint not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_price_bars_symbol_tf_time unique (symbol, timeframe, bar_time)
);

create table if not exists signals (
  id bigserial primary key,
  symbol text not null,
  signal_type text not null,
  strength numeric(12,6) not null default 0,
  signal_time timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists orders (
  id bigserial primary key,
  broker_order_id text not null unique,
  symbol text not null,
  qty numeric(16,6) not null,
  side text not null check (side in ('buy', 'sell')),
  order_type text not null default 'market',
  status text not null,
  submitted_at timestamptz not null default now(),
  filled_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists fills (
  id bigserial primary key,
  order_id bigint not null references orders(id) on delete cascade,
  symbol text not null,
  fill_qty numeric(16,6) not null,
  fill_price numeric(16,6) not null,
  fill_time timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table if not exists positions (
  id bigserial primary key,
  symbol text not null,
  qty numeric(16,6) not null default 0,
  avg_price numeric(16,6) not null default 0,
  market_value numeric(16,6),
  unrealized_pnl numeric(16,6),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_positions_symbol unique (symbol)
);

create table if not exists portfolio_snapshots (
  id bigserial primary key,
  snapshot_time timestamptz not null default now(),
  equity numeric(16,6) not null,
  cash numeric(16,6) not null,
  gross_exposure numeric(16,6) not null default 0,
  net_exposure numeric(16,6) not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists risk_events (
  id bigserial primary key,
  symbol text,
  severity text not null default 'warning',
  reason text not null,
  details jsonb not null default '{}'::jsonb,
  event_time timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table if not exists job_runs (
  id bigserial primary key,
  job_name text not null,
  run_type text not null default 'worker',
  status text not null,
  started_at timestamptz not null,
  finished_at timestamptz,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists settings (
  id bigserial primary key,
  key text not null unique,
  value jsonb not null,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_symbols_ticker on symbols(ticker);
create index if not exists idx_price_bars_symbol_time on price_bars(symbol, bar_time desc);
create index if not exists idx_signals_symbol_time on signals(symbol, signal_time desc);
create index if not exists idx_orders_symbol_created on orders(symbol, created_at desc);
create index if not exists idx_orders_status on orders(status);
create index if not exists idx_fills_order_id on fills(order_id);
create index if not exists idx_fills_symbol_time on fills(symbol, fill_time desc);
create index if not exists idx_positions_symbol on positions(symbol);
create index if not exists idx_portfolio_snapshots_time on portfolio_snapshots(snapshot_time desc);
create index if not exists idx_risk_events_symbol_time on risk_events(symbol, event_time desc);
create index if not exists idx_risk_events_severity_time on risk_events(severity, event_time desc);
create index if not exists idx_job_runs_job_name_time on job_runs(job_name, started_at desc);
