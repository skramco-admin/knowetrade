-- Align orders/fills schema for paper execution persistence.
alter table if exists orders
  add column if not exists order_type text not null default 'market';

alter table if exists orders
  add column if not exists submitted_at timestamptz not null default now();

alter table if exists orders
  add column if not exists filled_at timestamptz;

alter table if exists orders
  add column if not exists updated_at timestamptz not null default now();

alter table if exists fills
  add column if not exists symbol text not null default '';

alter table if exists fills
  add column if not exists fill_time timestamptz not null default now();
