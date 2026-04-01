-- Audit trail for operational toggles and admin actions.
create table if not exists audit_logs (
  id bigserial primary key,
  event_type text not null,
  actor text not null default 'system',
  details text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists idx_audit_logs_created_at on audit_logs(created_at desc);
