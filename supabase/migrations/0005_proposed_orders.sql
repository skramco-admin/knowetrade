-- Dry-run portfolio decisioning outputs; no broker transmission.
create table if not exists proposed_orders (
  id bigserial primary key,
  job_name text not null default 'dry_run_portfolio_decisioning',
  symbol text not null,
  action text not null,
  target_weight numeric(12,6) not null default 0,
  reason text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists idx_proposed_orders_created_at on proposed_orders(created_at desc);
create index if not exists idx_proposed_orders_symbol_created_at on proposed_orders(symbol, created_at desc);
