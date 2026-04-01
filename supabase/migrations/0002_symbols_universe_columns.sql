-- Expand symbol metadata for ETF-universe monitoring.
alter table if exists symbols
  add column if not exists asset_class text;

alter table if exists symbols
  add column if not exists strategy_bucket text;

alter table if exists symbols
  add column if not exists updated_at timestamptz not null default now();

update symbols
set
  asset_class = coalesce(asset_class, 'ETF'),
  strategy_bucket = coalesce(strategy_bucket, 'etf_trend'),
  updated_at = coalesce(updated_at, now());

alter table if exists symbols
  alter column asset_class set default 'ETF',
  alter column strategy_bucket set default 'etf_trend';

alter table if exists symbols
  alter column asset_class set not null,
  alter column strategy_bucket set not null;

create index if not exists idx_symbols_active_bucket
  on symbols(is_active, asset_class, strategy_bucket, ticker);
