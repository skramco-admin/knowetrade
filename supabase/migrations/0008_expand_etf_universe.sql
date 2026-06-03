-- Expand v1 etf_trend monitoring universe (12 -> 24 liquid ETFs).

insert into symbols (ticker, asset_class, strategy_bucket, is_active)
values
  ('SPY', 'ETF', 'etf_trend', true),
  ('QQQ', 'ETF', 'etf_trend', true),
  ('IWM', 'ETF', 'etf_trend', true),
  ('DIA', 'ETF', 'etf_trend', true),
  ('VOO', 'ETF', 'etf_trend', true),
  ('VTI', 'ETF', 'etf_trend', true),
  ('IVV', 'ETF', 'etf_trend', true),
  ('XLK', 'ETF', 'etf_trend', true),
  ('XLF', 'ETF', 'etf_trend', true),
  ('XLE', 'ETF', 'etf_trend', true),
  ('XLV', 'ETF', 'etf_trend', true),
  ('XLP', 'ETF', 'etf_trend', true),
  ('XLI', 'ETF', 'etf_trend', true),
  ('XLB', 'ETF', 'etf_trend', true),
  ('XLC', 'ETF', 'etf_trend', true),
  ('XLRE', 'ETF', 'etf_trend', true),
  ('XLU', 'ETF', 'etf_trend', true),
  ('XLY', 'ETF', 'etf_trend', true),
  ('SMH', 'ETF', 'etf_trend', true),
  ('XBI', 'ETF', 'etf_trend', true),
  ('EFA', 'ETF', 'etf_trend', true),
  ('VEA', 'ETF', 'etf_trend', true),
  ('TLT', 'ETF', 'etf_trend', true),
  ('GLD', 'ETF', 'etf_trend', true)
on conflict (ticker) do update set
  asset_class = excluded.asset_class,
  strategy_bucket = excluded.strategy_bucket,
  is_active = excluded.is_active,
  updated_at = now();

update symbols
set
  is_active = false,
  updated_at = now()
where asset_class = 'ETF'
  and strategy_bucket = 'etf_trend'
  and ticker not in (
    'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'IVV',
    'XLK', 'XLF', 'XLE', 'XLV', 'XLP', 'XLI', 'XLB', 'XLC', 'XLRE', 'XLU', 'XLY',
    'SMH', 'XBI', 'EFA', 'VEA', 'TLT', 'GLD'
  );
