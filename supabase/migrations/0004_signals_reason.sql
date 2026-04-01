-- Ensure signals table supports persisted reasoning for v1 signal generation.
create table if not exists signals (
  id bigserial primary key,
  symbol text not null,
  signal_type text not null,
  strength numeric(12,6) not null default 0,
  reason text,
  signal_time timestamptz not null default now(),
  created_at timestamptz not null default now()
);

alter table if exists signals
  add column if not exists reason text;

alter table if exists signals
  add column if not exists signal_time timestamptz not null default now();

create index if not exists idx_signals_symbol_time on signals(symbol, signal_time desc);
