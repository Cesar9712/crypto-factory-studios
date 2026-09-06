begin;

create or replace function public.fullgame_acquire_action_lease(
  p_character uuid,
  p_action text,
  p_request text,
  p_seconds integer default 60
) returns boolean
language plpgsql
security definer
set search_path=public
as $$
declare v_request text;
declare v_acquired text;
begin
  if p_character is null or not exists(select 1 from public.characters where id=p_character) then
    raise exception 'Character not found';
  end if;
  if char_length(coalesce(p_action,''))<1 or char_length(p_action)>48 then raise exception 'Invalid action key'; end if;
  v_request:=left(coalesce(nullif(trim(p_request),''),gen_random_uuid()::text),128);
  p_seconds:=least(greatest(coalesce(p_seconds,60),5),300);

  delete from public.game_action_leases where expires_at<now()-interval '5 minutes';
  insert into public.game_action_leases(character_id,action_key,request_key,expires_at,updated_at)
  values(p_character,p_action,v_request,now()+p_seconds*interval '1 second',now())
  on conflict(character_id,action_key) do update
    set request_key=excluded.request_key,expires_at=excluded.expires_at,updated_at=now()
    where public.game_action_leases.expires_at<=now()
  returning request_key into v_acquired;
  return coalesce(v_acquired=v_request,false);
end$$;

revoke all on function public.fullgame_acquire_action_lease(uuid,text,text,integer) from public,anon,authenticated;
grant execute on function public.fullgame_acquire_action_lease(uuid,text,text,integer) to service_role;

commit;
