-- Initial ETF universe for v1 (long-only, liquid broad market + sectors)
insert into symbols (ticker, is_active)
values
  ('SPY', true),
  ('QQQ', true),
  ('IVV', true),
  ('VTI', true),
  ('VOO', true),
  ('DIA', true),
  ('IWM', true),
  ('XLK', true),
  ('XLF', true),
  ('XLE', true),
  ('XLY', true),
  ('XLP', true),
  ('XLU', true),
  ('XLV', true),
  ('XLI', true),
  ('XLB', true),
  ('XLRE', true),
  ('XLC', true)
on conflict (ticker) do nothing;
