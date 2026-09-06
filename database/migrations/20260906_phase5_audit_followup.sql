begin;

create or replace function public.phase5_sync_codex(p_character uuid)
returns void language plpgsql security definer set search_path=public as $$
declare v_count integer;v_zone text;v_zone_name text;
begin
  insert into public.phase5_codex_catalog(category,entry_key,name_es,name_en,icon,source)
  select case when is_boss then 'bosses' else 'monsters' end,id,name,name,case when is_boss then '👑' else '👾' end,'Combate'
    from public.enemy_definitions
  on conflict(category,entry_key) do update set name_es=excluded.name_es,name_en=excluded.name_en,icon=excluded.icon,source=excluded.source;

  insert into public.phase5_codex_catalog(category,entry_key,name_es,name_en,icon,source)
  select 'equipment',id,name,name,'🛡️','Equipo'
    from public.item_definitions where type in('equipment','weapon','armor') or slot is not null
  on conflict(category,entry_key) do update set name_es=excluded.name_es,name_en=excluded.name_en;

  insert into public.phase5_codex_catalog(category,entry_key,name_es,name_en,icon,source)
  select 'sets',id,name_es,name_en,'✨','Sets' from public.phase3_set_definitions where active
  on conflict(category,entry_key) do update set name_es=excluded.name_es,name_en=excluded.name_en;

  insert into public.phase5_codex_catalog(category,entry_key,name_es,name_en,icon,source)
  select 'zones',id,name,name,'🗺️','Mundo' from public.zones
  on conflict(category,entry_key) do update set name_es=excluded.name_es,name_en=excluded.name_en,source=excluded.source;

  insert into public.character_codex_entries(character_id,category,entry_key)
  select p_character,case when e.is_boss then 'bosses' else 'monsters' end,m.enemy_id
    from public.monster_codex m join public.enemy_definitions e on e.id=m.enemy_id
   where m.character_id=p_character and m.kills>0 and m.enemy_id is not null
  on conflict do nothing;

  insert into public.character_codex_entries(character_id,category,entry_key)
  select p_character,'equipment',definition_id
    from public.item_instances
   where owner_character_id=p_character and definition_id is not null
  on conflict do nothing;

  insert into public.character_codex_entries(character_id,category,entry_key)
  select distinct p_character,'sets',set_id
    from public.item_instances
   where owner_character_id=p_character and set_id is not null
  on conflict do nothing;

  insert into public.character_codex_entries(character_id,category,entry_key)
  select p_character,'pets',pet_key from public.character_pets where character_id=p_character and pet_key is not null
  on conflict do nothing;

  insert into public.character_codex_entries(character_id,category,entry_key)
  select p_character,'resources',resource_key from public.resources where character_id=p_character and amount>0 and resource_key is not null
  on conflict do nothing;

  select coalesce(c.zone_id,c.location,'bastion'),coalesce(z.name,coalesce(c.zone_id,c.location,'bastion'))
    into v_zone,v_zone_name
    from public.characters c left join public.zones z on z.id=coalesce(c.zone_id,c.location,'bastion')
   where c.id=p_character;
  if v_zone is not null then
    insert into public.phase5_codex_catalog(category,entry_key,name_es,name_en,icon,source)
    values('zones',v_zone,v_zone_name,v_zone_name,'🗺️','Mundo')
    on conflict(category,entry_key) do update set name_es=excluded.name_es,name_en=excluded.name_en;
    insert into public.character_codex_entries(character_id,category,entry_key)
    values(p_character,'zones',v_zone) on conflict do nothing;
  end if;

  select count(*) into v_count from public.character_codex_entries where character_id=p_character;
  if v_count>=15 then perform public.phase5_try_pet_drop(p_character,'collection','codex15','collection:codex15:'||p_character::text); end if;
end$$;

create or replace function public.phase5_sync_notifications(p_character uuid)
returns void language plpgsql security definer set search_path=public as $$
declare r record;v_name text;v_rank integer;v_title text;
begin
  perform public.phase5_refresh_events();
  for r in
    select i.id,i.event_key,i.starts_at,i.ends_at,
           coalesce(d.name_es,t.name_es,i.event_key) as name_es,
           coalesce(d.event_type,i.config->>'event_type') as event_type
      from public.phase5_event_instances i
      left join public.phase5_weekly_event_definitions d on d.event_key=i.event_key
      left join public.phase5_event_templates t on t.template_key=i.template_key
     where i.status='active' and i.starts_at<=now() and i.ends_at>now()
  loop
    v_name:=coalesce(r.name_es,r.event_key);
    v_title:=case when r.event_type in('world_boss','clan_boss') then 'Boss activo' else 'Evento iniciado' end;
    insert into public.player_notifications(character_id,kind,title,body,dedupe_key)
    values(p_character,case when r.event_type in('world_boss','clan_boss') then 'boss' else 'event' end,v_title,v_name,'event:start:'||r.id::text)
    on conflict(character_id,dedupe_key) do update
      set kind=excluded.kind,title=excluded.title,body=excluded.body;

    if r.event_type is not null and public.phase5_event_eligible(p_character,r.event_type,r.starts_at,r.ends_at)
       and not exists(select 1 from public.phase5_event_claims where event_instance_id=r.id and character_id=p_character) then
      insert into public.player_notifications(character_id,kind,title,body,dedupe_key)
      values(p_character,'reward','Recompensa disponible',v_name,'event:claim:'||r.id::text)
      on conflict(character_id,dedupe_key) do update
        set kind=excluded.kind,title=excluded.title,body=excluded.body;
    end if;
  end loop;

  perform public.phase5_refresh_rankings_if_needed();
  select min(rank) into v_rank from public.phase5_rankings
   where entity_type='character' and entity_id=p_character and rank<=10;
  if v_rank is not null then
    insert into public.player_notifications(character_id,kind,title,body,dedupe_key)
    values(p_character,'ranking','Ranking actualizado','Estás en el Top '||v_rank,'rank:'||current_date::text)
    on conflict(character_id,dedupe_key) do update
      set kind=excluded.kind,title=excluded.title,body=excluded.body;
  end if;
end$$;

revoke all on function public.phase5_sync_codex(uuid),public.phase5_sync_notifications(uuid) from public,anon,authenticated;
grant execute on function public.phase5_sync_codex(uuid),public.phase5_sync_notifications(uuid) to service_role;

commit;
