-- Initial ETF universe for v1 (daily etf_trend strategy bucket)
insert into symbols (ticker, asset_class, strategy_bucket, is_active)
values
  ('SPY', 'ETF', 'etf_trend', true),
  ('QQQ', 'ETF', 'etf_trend', true),
  ('IWM', 'ETF', 'etf_trend', true),
  ('DIA', 'ETF', 'etf_trend', true),
  ('XLK', 'ETF', 'etf_trend', true),
  ('XLF', 'ETF', 'etf_trend', true),
  ('XLE', 'ETF', 'etf_trend', true),
  ('XLV', 'ETF', 'etf_trend', true),
  ('XLP', 'ETF', 'etf_trend', true),
  ('XLI', 'ETF', 'etf_trend', true),
  ('TLT', 'ETF', 'etf_trend', true),
  ('GLD', 'ETF', 'etf_trend', true)
on conflict (ticker) do update set
  asset_class = excluded.asset_class,
  strategy_bucket = excluded.strategy_bucket,
  is_active = excluded.is_active,
  updated_at = now();

-- Keep the v1 monitoring universe explicit: deactivate any extra ETFs in this bucket.
update symbols
set
  is_active = false,
  updated_at = now()
where asset_class = 'ETF'
  and strategy_bucket = 'etf_trend'
  and ticker not in ('SPY', 'QQQ', 'IWM', 'DIA', 'XLK', 'XLF', 'XLE', 'XLV', 'XLP', 'XLI', 'TLT', 'GLD');
