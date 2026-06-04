alter table orders add column if not exists filled_avg_price numeric(16,6);
alter table orders add column if not exists cost_basis_avg numeric(16,6);
alter table orders add column if not exists realized_pnl_usd numeric(16,6);
alter table orders add column if not exists realized_pnl_pct numeric(16,8);
