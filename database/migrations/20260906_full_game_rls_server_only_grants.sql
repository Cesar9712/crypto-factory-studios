begin;

-- RLS tables without policies are intentionally server-only. RLS denies row DML,
-- but table-level privileges such as TRUNCATE are not row-policy operations.
-- Remove all latent client grants while preserving service_role access.
do $$
declare r record;
begin
  for r in
    select n.nspname as schema_name,c.relname as table_name
    from pg_class c
    join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='public'
      and c.relkind in ('r','p')
      and c.relrowsecurity
      and not exists (
        select 1 from pg_policy p where p.polrelid=c.oid
      )
  loop
    execute format('revoke all privileges on table %I.%I from public, anon, authenticated',r.schema_name,r.table_name);
    execute format('grant all privileges on table %I.%I to service_role',r.schema_name,r.table_name);
  end loop;
end$$;

commit;
