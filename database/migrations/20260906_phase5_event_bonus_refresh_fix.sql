begin;

create or replace function public.phase5_event_bonus(p_bonus_key text)
returns numeric
language plpgsql
security definer
set search_path=public
as $$
declare v_bonus numeric:=0;
begin
  perform public.phase5_refresh_events();
  select coalesce(max(d.bonus_percent),0)
    into v_bonus
  from public.phase5_event_instances i
  join public.phase5_weekly_event_definitions d on d.event_key=i.event_key
  where i.status='active'
    and i.starts_at<=now()
    and i.ends_at>now()
    and d.bonus_key=p_bonus_key;
  return coalesce(v_bonus,0);
end$$;

revoke all on function public.phase5_event_bonus(text) from public,anon,authenticated;
grant execute on function public.phase5_event_bonus(text) to service_role;

commit;
