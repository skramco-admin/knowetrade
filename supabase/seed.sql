insert into symbols (ticker, is_active)
values
  ('SPY', true),
  ('QQQ', true),
  ('IVV', true),
  ('VTI', true)
on conflict (ticker) do nothing;
