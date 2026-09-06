-- Correct the Phase 4 passive-production arithmetic before deployment.
create or replace function public.phase4_settle_bastion(p_character uuid)
returns void language plpgsql security definer set search_path=public as $$
declare
  r record; v_now timestamptz:=now(); v_raw bigint; v_used bigint; v_ticks bigint; v_gain bigint;
  v_cap integer; v_offline integer; v_stock bigint; v_room bigint;
begin
  perform public.phase4_ensure_bastion(p_character);
  update public.bastion_buildings
    set level=upgrade_to,upgrade_to=null,upgrade_started_at=null,upgrade_finishes_at=null,updated_at=v_now
    where character_id=p_character and upgrade_to is not null and upgrade_finishes_at<=v_now;
  v_cap:=public.phase4_storage_cap(p_character);
  v_offline:=public.phase4_offline_cap_hours(p_character);
  select coalesce(sum(amount),0) into v_stock from public.bastion_stockpile where character_id=p_character;
  for r in
    select b.building_key,b.level,b.last_production_at,d.produces_resource,d.production_per_hour
    from public.bastion_buildings b join public.bastion_building_defs d using(building_key)
    where b.character_id=p_character and d.produces_resource is not null and d.production_per_hour>0
    for update of b
  loop
    v_raw:=greatest(0,floor(extract(epoch from (v_now-r.last_production_at)))::bigint);
    v_used:=least(v_raw,(v_offline*3600)::bigint);
    v_ticks:=floor(v_used/600.0)::bigint;
    if v_ticks>0 then
      v_gain:=floor(v_ticks*r.production_per_hour*r.level/6.0)::bigint;
      v_room:=greatest(0,v_cap-v_stock);
      v_gain:=least(v_gain,v_room);
      if v_gain>0 then
        insert into public.bastion_stockpile(character_id,resource_key,amount,updated_at)
        values(p_character,r.produces_resource,v_gain,v_now)
        on conflict(character_id,resource_key) do update set amount=public.bastion_stockpile.amount+excluded.amount,updated_at=v_now;
        v_stock:=v_stock+v_gain;
      end if;
      update public.bastion_buildings
      set last_production_at=case when v_raw>v_offline*3600 then v_now else last_production_at+(v_ticks*600)*interval '1 second' end,updated_at=v_now
      where character_id=p_character and building_key=r.building_key;
    elsif v_raw>v_offline*3600 then
      update public.bastion_buildings set last_production_at=v_now,updated_at=v_now
      where character_id=p_character and building_key=r.building_key;
    end if;
  end loop;
  delete from public.bastion_buffs where character_id=p_character and expires_at<=v_now;
end;$$;
revoke all on function public.phase4_settle_bastion(uuid) from public,anon,authenticated;
grant execute on function public.phase4_settle_bastion(uuid) to service_role;
