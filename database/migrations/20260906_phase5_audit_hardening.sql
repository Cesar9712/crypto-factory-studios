begin;

-- 1/9: Serialize rate-limit checks per character+bucket so concurrent requests cannot bypass limits.
create or replace function public.phase5_rate_gate(p_character uuid,p_bucket text,p_limit integer,p_seconds integer)
returns void language plpgsql security definer set search_path=public as $$
declare v_count integer;
begin
  if p_character is null or p_bucket is null or char_length(p_bucket)<1 or char_length(p_bucket)>64 or p_limit<1 or p_seconds<1 then
    raise exception 'Invalid rate gate';
  end if;
  perform pg_advisory_xact_lock(hashtextextended(p_character::text||':'||p_bucket,0));
  delete from public.phase5_rate_events
   where character_id=p_character and bucket=p_bucket
     and created_at<now()-make_interval(secs=>greatest(p_seconds*4,3600));
  select count(*) into v_count
    from public.phase5_rate_events
   where character_id=p_character and bucket=p_bucket
     and created_at>now()-make_interval(secs=>p_seconds);
  if v_count>=p_limit then raise exception 'Rate limit exceeded'; end if;
  insert into public.phase5_rate_events(character_id,bucket) values(p_character,p_bucket);
end$$;

-- State/presence refresh is also rate limited; 30/min is well above the mobile 15s refresh cadence.
create or replace function public.phase5_presence_touch(p_character uuid)
returns void language plpgsql security definer set search_path=public as $$
begin
  perform public.phase5_rate_gate(p_character,'state_refresh',30,60);
  insert into public.player_presence(character_id,status,last_seen_at,updated_at)
  values(p_character,'online',now(),now())
  on conflict(character_id) do update
    set status='online',last_seen_at=now(),updated_at=now();
end$$;

create or replace function public.phase5_friend_remove(p_character uuid,p_target uuid)
returns void language plpgsql security definer set search_path=public as $$
begin
  perform public.phase5_rate_gate(p_character,'friend_remove',12,60);
  delete from public.friendships
   where character_a=least(p_character,p_target)
     and character_b=greatest(p_character,p_target);
end$$;

-- 6: Keep achievement progress visible before unlock; titles unlock only at the real threshold.
create or replace function public.phase5_sync_titles(p_character uuid)
returns void language plpgsql security definer set search_path=public as $$
declare v_level integer:=0;v_boss bigint:=0;v_smith integer:=0;v_rift integer:=0;v_arena integer:=0;
begin
  select level into v_level from public.characters where id=p_character;
  select coalesce(sum(damage),0) into v_boss from public.world_event_contributions where character_id=p_character;
  select v_boss+coalesce(sum(damage),0) into v_boss from public.guild_raid_contributions where character_id=p_character;
  select coalesce(max(level),0) into v_smith from public.profession_progress where character_id=p_character and profession_key='smithing';
  select coalesce(max(highest_tier),0) into v_rift from public.phase2_rift_progress where character_id=p_character;
  select coalesce(max(highest_rating),0) into v_arena from public.phase2_arena_profiles where character_id=p_character;

  insert into public.character_achievements(character_id,achievement_id,progress,unlocked_at) values
    (p_character,'phase5_dragon_slayer',least(v_boss,2147483647)::integer,case when v_boss>=5000 then now() else null end),
    (p_character,'phase5_master_smith',v_smith,case when v_smith>=10 then now() else null end),
    (p_character,'phase5_immortal',v_level,case when v_level>=25 then now() else null end),
    (p_character,'phase5_rift_lord',v_rift,case when v_rift>=5 then now() else null end),
    (p_character,'phase5_arena_champion',v_arena,case when v_arena>=1200 then now() else null end)
  on conflict(character_id,achievement_id) do update
    set progress=excluded.progress,
        unlocked_at=coalesce(public.character_achievements.unlocked_at,excluded.unlocked_at);

  if v_boss>=5000 then insert into public.character_titles values(p_character,'dragon_slayer',now()) on conflict do nothing; end if;
  if v_smith>=10 then insert into public.character_titles values(p_character,'master_smith',now()) on conflict do nothing; end if;
  if v_level>=25 then insert into public.character_titles values(p_character,'immortal',now()) on conflict do nothing; end if;
  if v_rift>=5 then insert into public.character_titles values(p_character,'rift_lord',now()) on conflict do nothing; end if;
  if v_arena>=1200 then insert into public.character_titles values(p_character,'arena_champion',now()) on conflict do nothing; end if;
end$$;

-- 2: Make zone Codex entries data-driven so every real zone can be displayed/unlocked.
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
   where m.character_id=p_character and m.kills>0 on conflict do nothing;
  insert into public.character_codex_entries(character_id,category,entry_key)
  select p_character,'equipment',definition_id from public.item_instances where owner_character_id=p_character on conflict do nothing;
  insert into public.character_codex_entries(character_id,category,entry_key)
  select distinct p_character,'sets',set_id from public.item_instances where owner_character_id=p_character and set_id is not null on conflict do nothing;
  insert into public.character_codex_entries(character_id,category,entry_key)
  select p_character,'pets',pet_key from public.character_pets where character_id=p_character on conflict do nothing;
  insert into public.character_codex_entries(character_id,category,entry_key)
  select p_character,'resources',resource_key from public.resources where character_id=p_character and amount>0 on conflict do nothing;

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
  if v_count>=15 then
    perform public.phase5_try_pet_drop(p_character,'collection','codex15','collection:codex15:'||p_character::text);
  end if;
end$$;

-- 7: Temporary events are fully data-driven (no permanent dates) and now carry type, bonus and reward config.
update public.phase5_event_templates set config=config||case template_key
  when 'halloween' then '{"temporary":true,"event_type":"any_activity","bonus_key":"xp","bonus_percent":0.05,"reward":{"gold":100,"evolution_core":1}}'::jsonb
  when 'winter' then '{"temporary":true,"event_type":"gathering","bonus_key":"gathering","bonus_percent":0.08,"reward":{"gold":80}}'::jsonb
  when 'anniversary' then '{"temporary":true,"event_type":"any_activity","bonus_key":"xp","bonus_percent":0.05,"reward":{"gold":120,"evolution_core":1}}'::jsonb
  when 'rift_season' then '{"temporary":true,"event_type":"rift","bonus_key":"rift","bonus_percent":0.08,"reward":{"gold":100,"evolution_core":1}}'::jsonb
  else '{}'::jsonb end;

create or replace function public.phase5_schedule_template(p_template text,p_starts timestamptz,p_hours integer default null)
returns uuid language plpgsql security definer set search_path=public as $$
declare v_hours integer;v_id uuid;v_config jsonb;v_reward jsonb;
begin
  select coalesce(p_hours,default_duration_hours),config,coalesce(config->'reward','{}'::jsonb)
    into v_hours,v_config,v_reward
    from public.phase5_event_templates where template_key=p_template and enabled;
  if v_hours is null then raise exception 'Event template not found'; end if;
  if p_starts is null then raise exception 'Event start required'; end if;
  insert into public.phase5_event_instances(event_key,template_key,starts_at,ends_at,status,reward,config)
  values(p_template||':'||to_char(p_starts,'YYYYMMDDHH24MI'),p_template,p_starts,p_starts+v_hours*interval '1 hour',
         case when now()>=p_starts and now()<p_starts+v_hours*interval '1 hour' then 'active' else 'scheduled' end,
         v_reward,v_config)
  on conflict(event_key,starts_at) do update set ends_at=excluded.ends_at,reward=excluded.reward,config=excluded.config
  returning id into v_id;
  return v_id;
end$$;

create or replace function public.phase5_event_bonus(p_bonus_key text)
returns numeric language plpgsql security definer set search_path=public as $$
declare v_bonus numeric:=0;
begin
  perform public.phase5_refresh_events();
  select coalesce(max(coalesce(d.bonus_percent,(i.config->>'bonus_percent')::numeric,0)),0)
    into v_bonus
    from public.phase5_event_instances i
    left join public.phase5_weekly_event_definitions d on d.event_key=i.event_key
   where i.status='active' and i.starts_at<=now() and i.ends_at>now()
     and coalesce(d.bonus_key,i.config->>'bonus_key')=p_bonus_key;
  return coalesce(v_bonus,0);
end$$;

create or replace function public.phase5_event_eligible(p_character uuid,p_event_type text,p_start timestamptz,p_end timestamptz)
returns boolean language plpgsql stable security definer set search_path=public as $$
declare v_guild uuid;
begin
  case p_event_type
    when 'gathering' then return exists(select 1 from public.game_transactions where character_id=p_character and kind='gather' and created_at between p_start and p_end);
    when 'arena' then return exists(select 1 from public.phase2_arena_profiles where character_id=p_character and last_match_at between p_start and p_end);
    when 'rift' then return exists(select 1 from public.phase2_rift_runs where character_id=p_character and status='completed' and completed_at between p_start and p_end);
    when 'world_event' then return exists(select 1 from public.world_event_contributions where character_id=p_character and updated_at between p_start and p_end and attempts>0);
    when 'world_boss' then return exists(select 1 from public.world_event_contributions where character_id=p_character and updated_at between p_start and p_end and damage>0);
    when 'clan_boss' then return exists(select 1 from public.guild_raid_contributions where character_id=p_character and updated_at between p_start and p_end and attempts>0);
    when 'clan_war' then
      select guild_id into v_guild from public.guild_members where character_id=p_character;
      return v_guild is not null and exists(select 1 from public.guild_wars where (guild_a=v_guild or guild_b=v_guild) and week_start=public.current_game_week());
    when 'any_activity' then
      return exists(select 1 from public.game_transactions where character_id=p_character and created_at between p_start and p_end)
          or exists(select 1 from public.phase2_rift_runs where character_id=p_character and completed_at between p_start and p_end)
          or exists(select 1 from public.phase2_arena_profiles where character_id=p_character and last_match_at between p_start and p_end)
          or exists(select 1 from public.world_event_contributions where character_id=p_character and updated_at between p_start and p_end and attempts>0)
          or exists(select 1 from public.guild_raid_contributions where character_id=p_character and updated_at between p_start and p_end and attempts>0);
    else return false;
  end case;
end$$;

create or replace function public.phase5_claim_event(p_character uuid,p_event uuid,p_receipt text)
returns jsonb language plpgsql security definer set search_path=public as $$
declare v_type text;v_start timestamptz;v_end timestamptz;v_reward jsonb;v_gold integer;v_core integer;v_claimed uuid;v_pet text;v_receipt text;
begin
  perform public.phase5_rate_gate(p_character,'event_claim',6,30);
  perform public.phase5_refresh_events();
  select coalesce(d.event_type,i.config->>'event_type'),i.starts_at,i.ends_at,i.reward
    into v_type,v_start,v_end,v_reward
    from public.phase5_event_instances i
    left join public.phase5_weekly_event_definitions d on d.event_key=i.event_key
   where i.id=p_event and i.status='active' for update of i;
  if v_type is null then raise exception 'Event not active or misconfigured'; end if;
  if not public.phase5_event_eligible(p_character,v_type,v_start,v_end) then raise exception 'Event participation required'; end if;
  insert into public.phase5_action_receipts(receipt_key,character_id,action_type,payload)
  values('eventclaim:'||coalesce(nullif(p_receipt,''),p_event::text||':'||p_character::text),p_character,'event_claim',jsonb_build_object('event',p_event))
  on conflict do nothing returning receipt_key into v_receipt;
  if v_receipt is null then raise exception 'Duplicate event request'; end if;
  insert into public.phase5_event_claims(event_instance_id,character_id,reward)
  values(p_event,p_character,coalesce(v_reward,'{}'::jsonb))
  on conflict do nothing returning event_instance_id into v_claimed;
  if v_claimed is null then raise exception 'Event reward already claimed'; end if;
  v_gold:=coalesce((v_reward->>'gold')::integer,0);
  v_core:=coalesce((v_reward->>'evolution_core')::integer,0);
  if v_gold>0 then update public.characters set gold=gold+v_gold,updated_at=now() where id=p_character; end if;
  if v_core>0 then
    insert into public.item_instances(owner_character_id,definition_id,rarity,atk,def,metadata)
    select p_character,'pet_evolution_core','epic',0,0,'{"phase":5,"source":"event"}'::jsonb from generate_series(1,v_core);
  end if;
  v_pet:=public.phase5_try_pet_drop(p_character,'event',v_type,'event:'||p_event::text||':'||p_character::text);
  perform public.phase5_pet_add_xp(p_character,40,'event:'||p_event::text||':'||p_character::text);
  return jsonb_build_object('gold',v_gold,'evolutionCore',v_core,'pet',v_pet);
end$$;

-- 8: Notifications distinguish boss activity and also work for temporary template events.
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
    on conflict do nothing;
    if r.event_type is not null and public.phase5_event_eligible(p_character,r.event_type,r.starts_at,r.ends_at)
       and not exists(select 1 from public.phase5_event_claims where event_instance_id=r.id and character_id=p_character) then
      insert into public.player_notifications(character_id,kind,title,body,dedupe_key)
      values(p_character,'reward','Recompensa disponible',v_name,'event:claim:'||r.id::text) on conflict do nothing;
    end if;
  end loop;
  perform public.phase5_refresh_rankings_if_needed();
  select min(rank) into v_rank from public.phase5_rankings where entity_type='character' and entity_id=p_character and rank<=10;
  if v_rank is not null then
    insert into public.player_notifications(character_id,kind,title,body,dedupe_key)
    values(p_character,'ranking','Ranking actualizado','Estás en el Top '||v_rank,'rank:'||current_date::text) on conflict do nothing;
  end if;
end$$;

revoke all on function public.phase5_rate_gate(uuid,text,integer,integer),public.phase5_presence_touch(uuid),public.phase5_friend_remove(uuid,uuid),public.phase5_sync_titles(uuid),public.phase5_sync_codex(uuid),public.phase5_schedule_template(text,timestamptz,integer),public.phase5_event_bonus(text),public.phase5_event_eligible(uuid,text,timestamptz,timestamptz),public.phase5_claim_event(uuid,uuid,text),public.phase5_sync_notifications(uuid) from public,anon,authenticated;
grant execute on function public.phase5_rate_gate(uuid,text,integer,integer),public.phase5_presence_touch(uuid),public.phase5_friend_remove(uuid,uuid),public.phase5_sync_titles(uuid),public.phase5_sync_codex(uuid),public.phase5_schedule_template(text,timestamptz,integer),public.phase5_event_bonus(text),public.phase5_event_eligible(uuid,text,timestamptz,timestamptz),public.phase5_claim_event(uuid,uuid,text),public.phase5_sync_notifications(uuid) to service_role;

commit;
