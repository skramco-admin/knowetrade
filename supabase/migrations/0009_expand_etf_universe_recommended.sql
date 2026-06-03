-- Expand etf_trend universe: keep all existing names + add liquid sector/thematic/intl/bond ETFs.

insert into symbols (ticker, asset_class, strategy_bucket, is_active)
values
  -- US broad market & size
  ('SPY', 'ETF', 'etf_trend', true),
  ('QQQ', 'ETF', 'etf_trend', true),
  ('IWM', 'ETF', 'etf_trend', true),
  ('DIA', 'ETF', 'etf_trend', true),
  ('VOO', 'ETF', 'etf_trend', true),
  ('VTI', 'ETF', 'etf_trend', true),
  ('IVV', 'ETF', 'etf_trend', true),
  ('MDY', 'ETF', 'etf_trend', true),
  ('RSP', 'ETF', 'etf_trend', true),
  ('MGK', 'ETF', 'etf_trend', true),
  ('VUG', 'ETF', 'etf_trend', true),
  ('SCHD', 'ETF', 'etf_trend', true),
  -- GICS sectors (full set)
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
  -- Thematic / industry
  ('SMH', 'ETF', 'etf_trend', true),
  ('XBI', 'ETF', 'etf_trend', true),
  ('ARKK', 'ETF', 'etf_trend', true),
  ('XRT', 'ETF', 'etf_trend', true),
  ('KRE', 'ETF', 'etf_trend', true),
  ('ITB', 'ETF', 'etf_trend', true),
  -- International
  ('EFA', 'ETF', 'etf_trend', true),
  ('VEA', 'ETF', 'etf_trend', true),
  ('EEM', 'ETF', 'etf_trend', true),
  ('EWJ', 'ETF', 'etf_trend', true),
  -- Rates, credit & diversifiers
  ('TLT', 'ETF', 'etf_trend', true),
  ('IEF', 'ETF', 'etf_trend', true),
  ('LQD', 'ETF', 'etf_trend', true),
  ('HYG', 'ETF', 'etf_trend', true),
  ('GLD', 'ETF', 'etf_trend', true),
  ('SLV', 'ETF', 'etf_trend', true)
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
    'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'IVV', 'MDY', 'RSP', 'MGK', 'VUG', 'SCHD',
    'XLK', 'XLF', 'XLE', 'XLV', 'XLP', 'XLI', 'XLB', 'XLC', 'XLRE', 'XLU', 'XLY',
    'SMH', 'XBI', 'ARKK', 'XRT', 'KRE', 'ITB',
    'EFA', 'VEA', 'EEM', 'EWJ',
    'TLT', 'IEF', 'LQD', 'HYG', 'GLD', 'SLV'
  );
