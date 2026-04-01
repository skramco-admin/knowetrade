-- Ensure price_bars table exists for daily ETF ingestion.
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

create index if not exists idx_price_bars_symbol_time on price_bars(symbol, bar_time desc);
