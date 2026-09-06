begin;

create or replace function public.phase5_rate_gate(p_character uuid,p_bucket text,p_limit integer,p_seconds integer)
returns void language plpgsql security definer set search_path=public as $$
declare v_count integer;
begin
  if p_character is null or p_limit<1 or p_seconds<1 then raise exception 'Invalid rate gate'; end if;
  select count(*) into v_count from public.phase5_rate_events where character_id=p_character and bucket=p_bucket and created_at>now()-(p_seconds||' seconds')::interval;
  if v_count>=p_limit then raise exception 'Rate limit exceeded'; end if;
  insert into public.phase5_rate_events(character_id,bucket) values(p_character,p_bucket);
end$$;

create or replace function public.phase5_pet_bonus(p_character uuid,p_bonus_key text)
returns numeric language sql stable security definer set search_path=public as $$
  select coalesce(max(d.passive_percent),0)
  from public.character_pets p join public.pet_definitions d on d.pet_key=p.pet_key
  where p.character_id=p_character and p.equipped and d.enabled and d.passive_key=p_bonus_key
$$;

create or replace function public.phase5_pet_equip(p_character uuid,p_pet uuid)
returns void language plpgsql security definer set search_path=public as $$
begin
  perform public.phase5_rate_gate(p_character,'pet_equip',12,10);
  if not exists(select 1 from public.character_pets where id=p_pet and character_id=p_character) then raise exception 'Pet not found'; end if;
  update public.character_pets set equipped=false,updated_at=now() where character_id=p_character and equipped;
  update public.character_pets set equipped=true,updated_at=now() where id=p_pet and character_id=p_character;
end$$;

create or replace function public.phase5_pet_add_xp(p_character uuid,p_amount integer,p_receipt text)
returns integer language plpgsql security definer set search_path=public as $$
declare v_pet uuid;v_xp bigint;v_max integer;v_level integer;v_inserted text;
begin
  if p_amount<=0 then return 0; end if;
  insert into public.phase5_action_receipts(receipt_key,character_id,action_type,payload) values('petxp:'||p_receipt,p_character,'pet_xp',jsonb_build_object('amount',p_amount)) on conflict do nothing returning receipt_key into v_inserted;
  if v_inserted is null then return 0; end if;
  select p.id,p.xp,d.max_level into v_pet,v_xp,v_max from public.character_pets p join public.pet_definitions d on d.pet_key=p.pet_key where p.character_id=p_character and p.equipped limit 1 for update of p;
  if v_pet is null then return 0; end if;
  v_xp:=v_xp+p_amount;
  v_level:=least(v_max,1+floor(sqrt(v_xp::numeric/100.0))::integer);
  update public.character_pets set xp=v_xp,level=greatest(level,v_level),updated_at=now() where id=v_pet;
  return p_amount;
end$$;

create or replace function public.phase5_try_pet_drop(p_character uuid,p_source text,p_source_key text,p_receipt text)
returns text language plpgsql security definer set search_path=public as $$
declare v_pet text;v_chance integer;v_roll integer;v_inserted text;
begin
  case p_source
    when 'rift' then v_pet:='rift_hawk';v_chance:=7;
    when 'quest' then v_pet:='astral_fox';v_chance:=4;
    when 'world_boss' then v_pet:='draconid';v_chance:=3;
    when 'clan_boss' then v_pet:='ash_wolf';v_chance:=5;
    when 'collection' then v_pet:='ancient_spirit';v_chance:=100;
    when 'event' then v_pet:='rift_hawk';v_chance:=8;
    else return null;
  end case;
  insert into public.phase5_action_receipts(receipt_key,character_id,action_type,payload)
  values('petdrop:'||p_receipt,p_character,'pet_drop',jsonb_build_object('source',p_source,'sourceKey',p_source_key))
  on conflict do nothing returning receipt_key into v_inserted;
  if v_inserted is null then return null; end if;
  v_roll:=mod(abs(hashtextextended(p_receipt,0)),100)::integer+1;
  if v_roll>v_chance then return null; end if;
  insert into public.character_pets(character_id,pet_key,acquired_from)
  values(p_character,v_pet,p_source||':'||coalesce(p_source_key,''))
  on conflict(character_id,pet_key) do update set xp=public.character_pets.xp+25,updated_at=now();
  return v_pet;
end$$;

create or replace function public.phase5_pet_evolve(p_character uuid,p_pet uuid,p_receipt text)
returns integer language plpgsql security definer set search_path=public as $$
declare v_key text;v_level integer;v_stage integer;v_req_level integer;v_resource text;v_req_amount integer;v_have bigint;v_item_def text;v_item uuid;v_inserted text;
begin
  perform public.phase5_rate_gate(p_character,'pet_evolve',4,30);
  select p.pet_key,p.level,p.evolution_stage,d.evolution_level,d.evolution_resource_key,d.evolution_resource_amount,d.evolution_item_id
  into v_key,v_level,v_stage,v_req_level,v_resource,v_req_amount,v_item_def
  from public.character_pets p join public.pet_definitions d on d.pet_key=p.pet_key
  where p.id=p_pet and p.character_id=p_character and d.evolvable for update of p;
  if v_key is null then raise exception 'Pet not found'; end if;
  if v_stage>=3 then raise exception 'Pet evolution maxed'; end if;
  v_req_level:=v_req_level+v_stage*10; v_req_amount:=v_req_amount*(v_stage+1);
  if v_level<v_req_level then raise exception 'Pet level % required',v_req_level; end if;
  select amount into v_have from public.resources where character_id=p_character and resource_key=v_resource for update;
  if coalesce(v_have,0)<v_req_amount then raise exception 'Not enough evolution resources'; end if;
  select id into v_item from public.item_instances where owner_character_id=p_character and definition_id=v_item_def order by created_at limit 1 for update;
  if v_item is null then raise exception 'Evolution item required'; end if;
  insert into public.phase5_action_receipts(receipt_key,character_id,action_type,payload) values('evolve:'||p_receipt,p_character,'pet_evolve',jsonb_build_object('pet',p_pet,'stage',v_stage+1)) on conflict do nothing returning receipt_key into v_inserted;
  if v_inserted is null then raise exception 'Duplicate evolution request'; end if;
  update public.resources set amount=amount-v_req_amount where character_id=p_character and resource_key=v_resource;
  delete from public.item_instances where id=v_item;
  update public.character_pets set evolution_stage=evolution_stage+1,updated_at=now() where id=p_pet;
  return v_stage+1;
end$$;

create or replace function public.phase5_presence_touch(p_character uuid)
returns void language plpgsql security definer set search_path=public as $$
begin
  insert into public.player_presence(character_id,status,last_seen_at,updated_at) values(p_character,'online',now(),now())
  on conflict(character_id) do update set status='online',last_seen_at=now(),updated_at=now();
end$$;

create or replace function public.phase5_friend_request(p_character uuid,p_target uuid)
returns uuid language plpgsql security definer set search_path=public as $$
declare v_id uuid;v_a uuid;v_b uuid;
begin
  perform public.phase5_rate_gate(p_character,'friend_request',8,60);
  if p_character=p_target or not exists(select 1 from public.characters where id=p_target) then raise exception 'Invalid friend target'; end if;
  v_a:=least(p_character,p_target);v_b:=greatest(p_character,p_target);
  if exists(select 1 from public.friendships where character_a=v_a and character_b=v_b) then raise exception 'Already friends'; end if;
  if exists(select 1 from public.friend_requests where requester_id=p_target and addressee_id=p_character and status='pending') then raise exception 'This player already sent you a request'; end if;
  insert into public.friend_requests(requester_id,addressee_id) values(p_character,p_target) returning id into v_id;
  return v_id;
end$$;

create or replace function public.phase5_friend_respond(p_character uuid,p_request uuid,p_accept boolean)
returns void language plpgsql security definer set search_path=public as $$
declare v_from uuid;v_a uuid;v_b uuid;
begin
  perform public.phase5_rate_gate(p_character,'friend_respond',12,60);
  select requester_id into v_from from public.friend_requests where id=p_request and addressee_id=p_character and status='pending' for update;
  if v_from is null then raise exception 'Friend request not found'; end if;
  update public.friend_requests set status=case when p_accept then 'accepted' else 'declined' end,responded_at=now() where id=p_request;
  if p_accept then
    v_a:=least(p_character,v_from);v_b:=greatest(p_character,v_from);
    insert into public.friendships(character_a,character_b) values(v_a,v_b) on conflict do nothing;
  end if;
end$$;

create or replace function public.phase5_friend_remove(p_character uuid,p_target uuid)
returns void language plpgsql security definer set search_path=public as $$
begin
  delete from public.friendships where character_a=least(p_character,p_target) and character_b=greatest(p_character,p_target);
end$$;

create or replace function public.phase5_chat_send(p_character uuid,p_channel text,p_body text)
returns uuid language plpgsql security definer set search_path=public as $$
declare v_body text;v_guild uuid;v_id uuid;
begin
  perform public.phase5_rate_gate(p_character,'chat_send',5,10);
  if p_channel not in('global','clan') then raise exception 'Invalid chat channel'; end if;
  v_body:=regexp_replace(coalesce(p_body,''),E'[<>\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F]','','g');
  v_body:=regexp_replace(trim(v_body),E'\\s+',' ','g');
  if char_length(v_body)<1 or char_length(v_body)>280 then raise exception 'Message length invalid'; end if;
  if exists(select 1 from public.chat_messages where character_id=p_character and channel=p_channel and lower(body)=lower(v_body) and created_at>now()-interval '30 seconds') then raise exception 'Duplicate message'; end if;
  if p_channel='clan' then select guild_id into v_guild from public.guild_members where character_id=p_character; if v_guild is null then raise exception 'Not in a clan'; end if; end if;
  insert into public.chat_messages(character_id,channel,guild_id,body) values(p_character,p_channel,v_guild,v_body) returning id into v_id;
  return v_id;
end$$;

create or replace function public.phase5_chat_mute(p_character uuid,p_target uuid,p_minutes integer default 1440)
returns void language plpgsql security definer set search_path=public as $$
begin
  perform public.phase5_rate_gate(p_character,'chat_mute',12,60);
  if p_target=p_character then raise exception 'Cannot mute yourself'; end if;
  insert into public.chat_mutes(muter_character_id,muted_character_id,expires_at) values(p_character,p_target,now()+least(greatest(p_minutes,1),43200)*interval '1 minute')
  on conflict(muter_character_id,muted_character_id) do update set expires_at=excluded.expires_at,created_at=now();
end$$;

create or replace function public.phase5_chat_report(p_character uuid,p_message uuid,p_reason text)
returns void language plpgsql security definer set search_path=public as $$
declare v_reason text;
begin
  perform public.phase5_rate_gate(p_character,'chat_report',5,3600);
  v_reason:=left(regexp_replace(trim(coalesce(p_reason,'')),E'[<>\\x00-\\x1F]','','g'),240);
  if char_length(v_reason)<3 then raise exception 'Report reason required'; end if;
  if not exists(select 1 from public.chat_messages where id=p_message) then raise exception 'Message not found'; end if;
  insert into public.chat_reports(reporter_character_id,message_id,reason) values(p_character,p_message,v_reason) on conflict do nothing;
end$$;

create or replace function public.phase5_refresh_events()
returns void language plpgsql security definer set search_path=public as $$
declare v_week date:=public.current_game_week();r record;v_start timestamptz;
begin
  for r in select * from public.phase5_weekly_event_definitions where enabled loop
    v_start:=(v_week+(r.weekday-1))::timestamptz;
    insert into public.phase5_event_instances(event_key,starts_at,ends_at,status,reward,config)
    values(r.event_key,v_start,v_start+interval '1 day',case when now()>=v_start and now()<v_start+interval '1 day' then 'active' when now()>=v_start+interval '1 day' then 'ended' else 'scheduled' end,r.reward,r.config)
    on conflict(event_key,starts_at) do update set status=case when excluded.status='cancelled' then public.phase5_event_instances.status when now()>=public.phase5_event_instances.starts_at and now()<public.phase5_event_instances.ends_at then 'active' when now()>=public.phase5_event_instances.ends_at then 'ended' else 'scheduled' end,reward=excluded.reward,config=excluded.config;
  end loop;
  update public.phase5_event_instances set status='ended' where status in('scheduled','active') and ends_at<=now();
  update public.phase5_event_instances set status='active' where status='scheduled' and starts_at<=now() and ends_at>now();
end$$;

create or replace function public.phase5_event_bonus(p_bonus_key text)
returns numeric language sql stable security definer set search_path=public as $$
  select coalesce(max(d.bonus_percent),0) from public.phase5_event_instances i join public.phase5_weekly_event_definitions d on d.event_key=i.event_key where i.status='active' and i.starts_at<=now() and i.ends_at>now() and d.bonus_key=p_bonus_key
$$;

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
    when 'clan_war' then select guild_id into v_guild from public.guild_members where character_id=p_character; return v_guild is not null and exists(select 1 from public.guild_wars where (guild_a=v_guild or guild_b=v_guild) and week_start=public.current_game_week());
    else return false;
  end case;
end$$;

create or replace function public.phase5_claim_event(p_character uuid,p_event uuid,p_receipt text)
returns jsonb language plpgsql security definer set search_path=public as $$
declare v_type text;v_start timestamptz;v_end timestamptz;v_reward jsonb;v_gold integer;v_core integer;v_claimed uuid;v_pet text;
begin
  perform public.phase5_rate_gate(p_character,'event_claim',6,30);
  perform public.phase5_refresh_events();
  select d.event_type,i.starts_at,i.ends_at,i.reward into v_type,v_start,v_end,v_reward from public.phase5_event_instances i join public.phase5_weekly_event_definitions d on d.event_key=i.event_key where i.id=p_event and i.status='active' for update of i;
  if v_type is null then raise exception 'Event not active'; end if;
  if not public.phase5_event_eligible(p_character,v_type,v_start,v_end) then raise exception 'Event participation required'; end if;
  insert into public.phase5_event_claims(event_instance_id,character_id,reward) values(p_event,p_character,v_reward) on conflict do nothing returning event_instance_id into v_claimed;
  if v_claimed is null then raise exception 'Event reward already claimed'; end if;
  v_gold:=coalesce((v_reward->>'gold')::integer,0);v_core:=coalesce((v_reward->>'evolution_core')::integer,0);
  if v_gold>0 then update public.characters set gold=gold+v_gold,updated_at=now() where id=p_character; end if;
  if v_core>0 then insert into public.item_instances(owner_character_id,definition_id,rarity,atk,def,metadata) select p_character,'pet_evolution_core','epic',0,0,'{"phase":5,"source":"event"}'::jsonb from generate_series(1,v_core); end if;
  v_pet:=public.phase5_try_pet_drop(p_character,'event',v_type,'event:'||p_event::text||':'||p_character::text);
  perform public.phase5_pet_add_xp(p_character,40,'event:'||p_event::text||':'||p_character::text);
  return jsonb_build_object('gold',v_gold,'evolutionCore',v_core,'pet',v_pet);
end$$;

create or replace function public.phase5_schedule_template(p_template text,p_starts timestamptz,p_hours integer default null)
returns uuid language plpgsql security definer set search_path=public as $$
declare v_hours integer;v_id uuid;
begin
  select coalesce(p_hours,default_duration_hours) into v_hours from public.phase5_event_templates where template_key=p_template and enabled;
  if v_hours is null then raise exception 'Event template not found'; end if;
  insert into public.phase5_event_instances(event_key,template_key,starts_at,ends_at,status,config)
  select p_template||':'||to_char(p_starts,'YYYYMMDDHH24MI'),p_template,p_starts,p_starts+v_hours*interval '1 hour',case when now()>=p_starts and now()<p_starts+v_hours*interval '1 hour' then 'active' else 'scheduled' end,config from public.phase5_event_templates where template_key=p_template returning id into v_id;
  return v_id;
end$$;

insert into public.achievements(id,name,description,target,metadata) values
 ('phase5_dragon_slayer','Matadragones','Inflige 5000 de daño acumulado a bosses.',5000,'{"title":"dragon_slayer"}'::jsonb),
 ('phase5_master_smith','Maestro Herrero','Alcanza nivel 10 de Herrería.',10,'{"title":"master_smith"}'::jsonb),
 ('phase5_immortal','Inmortal','Alcanza nivel 25.',25,'{"title":"immortal"}'::jsonb),
 ('phase5_rift_lord','Señor de la Grieta','Alcanza Grieta tier 5.',5,'{"title":"rift_lord"}'::jsonb),
 ('phase5_arena_champion','Campeón de Arena','Alcanza rating 1200.',1200,'{"title":"arena_champion"}'::jsonb)
on conflict(id) do update set name=excluded.name,description=excluded.description,target=excluded.target,metadata=excluded.metadata;

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
  if v_boss>=5000 then insert into public.character_titles values(p_character,'dragon_slayer',now()) on conflict do nothing; insert into public.character_achievements(character_id,achievement_id,progress,unlocked_at) values(p_character,'phase5_dragon_slayer',least(v_boss,2147483647)::integer,now()) on conflict(character_id,achievement_id) do update set progress=excluded.progress,unlocked_at=coalesce(public.character_achievements.unlocked_at,excluded.unlocked_at); end if;
  if v_smith>=10 then insert into public.character_titles values(p_character,'master_smith',now()) on conflict do nothing; insert into public.character_achievements values(p_character,'phase5_master_smith',v_smith,now()) on conflict(character_id,achievement_id) do update set progress=excluded.progress,unlocked_at=coalesce(public.character_achievements.unlocked_at,excluded.unlocked_at); end if;
  if v_level>=25 then insert into public.character_titles values(p_character,'immortal',now()) on conflict do nothing; insert into public.character_achievements values(p_character,'phase5_immortal',v_level,now()) on conflict(character_id,achievement_id) do update set progress=excluded.progress,unlocked_at=coalesce(public.character_achievements.unlocked_at,excluded.unlocked_at); end if;
  if v_rift>=5 then insert into public.character_titles values(p_character,'rift_lord',now()) on conflict do nothing; insert into public.character_achievements values(p_character,'phase5_rift_lord',v_rift,now()) on conflict(character_id,achievement_id) do update set progress=excluded.progress,unlocked_at=coalesce(public.character_achievements.unlocked_at,excluded.unlocked_at); end if;
  if v_arena>=1200 then insert into public.character_titles values(p_character,'arena_champion',now()) on conflict do nothing; insert into public.character_achievements values(p_character,'phase5_arena_champion',v_arena,now()) on conflict(character_id,achievement_id) do update set progress=excluded.progress,unlocked_at=coalesce(public.character_achievements.unlocked_at,excluded.unlocked_at); end if;
end$$;

create or replace function public.phase5_set_title(p_character uuid,p_title text)
returns void language plpgsql security definer set search_path=public as $$
begin
  if p_title is not null and not exists(select 1 from public.character_titles where character_id=p_character and title_key=p_title) then raise exception 'Title not unlocked'; end if;
  update public.characters set selected_title_key=p_title,updated_at=now() where id=p_character;
end$$;

create or replace function public.phase5_sync_codex(p_character uuid)
returns void language plpgsql security definer set search_path=public as $$
declare v_count integer;
begin
  insert into public.phase5_codex_catalog(category,entry_key,name_es,name_en,icon,source)
  select case when is_boss then 'bosses' else 'monsters' end,id,name,name,case when is_boss then '👑' else '👾' end,'Combate' from public.enemy_definitions
  on conflict(category,entry_key) do nothing;
  insert into public.phase5_codex_catalog(category,entry_key,name_es,name_en,icon,source)
  select 'equipment',id,name,name,'🛡️','Equipo' from public.item_definitions where type in('equipment','weapon','armor') or slot is not null
  on conflict(category,entry_key) do nothing;
  insert into public.phase5_codex_catalog(category,entry_key,name_es,name_en,icon,source)
  select 'sets',id,name_es,name_en,'✨','Sets' from public.phase3_set_definitions where active
  on conflict(category,entry_key) do nothing;
  insert into public.character_codex_entries(character_id,category,entry_key)
  select p_character,case when e.is_boss then 'bosses' else 'monsters' end,m.enemy_id from public.monster_codex m join public.enemy_definitions e on e.id=m.enemy_id where m.character_id=p_character and m.kills>0 on conflict do nothing;
  insert into public.character_codex_entries(character_id,category,entry_key)
  select p_character,'equipment',definition_id from public.item_instances where owner_character_id=p_character on conflict do nothing;
  insert into public.character_codex_entries(character_id,category,entry_key)
  select distinct p_character,'sets',set_id from public.item_instances where owner_character_id=p_character and set_id is not null on conflict do nothing;
  insert into public.character_codex_entries(character_id,category,entry_key)
  select p_character,'pets',pet_key from public.character_pets where character_id=p_character on conflict do nothing;
  insert into public.character_codex_entries(character_id,category,entry_key)
  select p_character,'resources',resource_key from public.resources where character_id=p_character and amount>0 on conflict do nothing;
  insert into public.character_codex_entries(character_id,category,entry_key)
  select p_character,'zones',coalesce(zone_id,location,'bastion') from public.characters where id=p_character on conflict do nothing;
  select count(*) into v_count from public.character_codex_entries where character_id=p_character;
  if v_count>=15 then perform public.phase5_try_pet_drop(p_character,'collection','codex15','collection:codex15:'||p_character::text); end if;
end$$;

create or replace function public.phase5_refresh_rankings()
returns void language plpgsql security definer set search_path=public as $$
declare v_now timestamptz:=now();
begin
  perform pg_advisory_xact_lock(50505);
  delete from public.phase5_rankings;
  insert into public.phase5_rankings(ranking_key,entity_type,entity_id,score,rank,snapshot_at)
  select 'level','character',id,level,row_number() over(order by level desc,xp desc,id),v_now from public.characters order by level desc,xp desc limit 100;
  insert into public.phase5_rankings select 'power','character',c.id,(c.level*100+coalesce(s.atk,0)*4+coalesce(s.def,0)*4+(coalesce(s.strength,0)+coalesce(s.vitality,0)+coalesce(s.agility,0)+coalesce(s.intelligence,0)+coalesce(s.luck,0))*2+c.renown*5)::numeric,row_number() over(order by (c.level*100+coalesce(s.atk,0)*4+coalesce(s.def,0)*4+(coalesce(s.strength,0)+coalesce(s.vitality,0)+coalesce(s.agility,0)+coalesce(s.intelligence,0)+coalesce(s.luck,0))*2+c.renown*5) desc,c.id),v_now from public.characters c left join public.character_stats s on s.character_id=c.id order by 4 desc limit 100;
  insert into public.phase5_rankings select 'arena','character',character_id,max(highest_rating)::numeric,row_number() over(order by max(highest_rating) desc,character_id),v_now from public.phase2_arena_profiles group by character_id order by 4 desc limit 100;
  insert into public.phase5_rankings select 'world_boss','character',character_id,sum(damage)::numeric,row_number() over(order by sum(damage) desc,character_id),v_now from public.world_event_contributions group by character_id order by 4 desc limit 100;
  insert into public.phase5_rankings select 'clans','guild',id,(level*1000+xp)::numeric,row_number() over(order by level desc,xp desc,id),v_now from public.guilds order by 4 desc limit 100;
  insert into public.phase5_rankings select 'professions','character',character_id,(sum(level)*1000+sum(xp))::numeric,row_number() over(order by sum(level) desc,sum(xp) desc,character_id),v_now from public.profession_progress group by character_id order by 4 desc limit 100;
  insert into public.phase5_rankings select 'collection','character',c.id,((select count(*) from public.character_codex_entries x where x.character_id=c.id)*10+(select count(*) from public.character_pets p where p.character_id=c.id)*100)::numeric,row_number() over(order by ((select count(*) from public.character_codex_entries x where x.character_id=c.id)*10+(select count(*) from public.character_pets p where p.character_id=c.id)*100) desc,c.id),v_now from public.characters c order by 4 desc limit 100;
  insert into public.phase5_rankings select 'season','character',character_id,max(level*1000+xp)::numeric,row_number() over(order by max(level*1000+xp) desc,character_id),v_now from public.battle_pass_progress group by character_id order by 4 desc limit 100;
  insert into public.phase5_meta(meta_key,value,updated_at) values('rankings',jsonb_build_object('snapshotAt',v_now),v_now) on conflict(meta_key) do update set value=excluded.value,updated_at=v_now;
end$$;

create or replace function public.phase5_refresh_rankings_if_needed()
returns void language plpgsql security definer set search_path=public as $$
declare v_last timestamptz;
begin
  select updated_at into v_last from public.phase5_meta where meta_key='rankings';
  if v_last is null or v_last<now()-interval '60 seconds' then perform public.phase5_refresh_rankings(); end if;
end$$;

create or replace function public.phase5_sync_notifications(p_character uuid)
returns void language plpgsql security definer set search_path=public as $$
declare r record;v_name text;v_rank integer;
begin
  perform public.phase5_refresh_events();
  for r in select i.id,i.event_key,i.starts_at,i.ends_at,d.name_es,d.event_type from public.phase5_event_instances i left join public.phase5_weekly_event_definitions d on d.event_key=i.event_key where i.status='active' and i.starts_at<=now() and i.ends_at>now() loop
    v_name:=coalesce(r.name_es,r.event_key);
    insert into public.player_notifications(character_id,kind,title,body,dedupe_key) values(p_character,'event','Evento iniciado',v_name,'event:start:'||r.id::text) on conflict do nothing;
    if r.event_type is not null and public.phase5_event_eligible(p_character,r.event_type,r.starts_at,r.ends_at) and not exists(select 1 from public.phase5_event_claims where event_instance_id=r.id and character_id=p_character) then
      insert into public.player_notifications(character_id,kind,title,body,dedupe_key) values(p_character,'reward','Recompensa disponible',v_name,'event:claim:'||r.id::text) on conflict do nothing;
    end if;
  end loop;
  perform public.phase5_refresh_rankings_if_needed();
  select min(rank) into v_rank from public.phase5_rankings where entity_type='character' and entity_id=p_character and rank<=10;
  if v_rank is not null then insert into public.player_notifications(character_id,kind,title,body,dedupe_key) values(p_character,'ranking','Ranking actualizado','Estás en el Top '||v_rank,'rank:'||current_date::text) on conflict do nothing; end if;
end$$;

revoke all on function public.phase5_rate_gate(uuid,text,integer,integer),public.phase5_pet_bonus(uuid,text),public.phase5_pet_equip(uuid,uuid),public.phase5_pet_add_xp(uuid,integer,text),public.phase5_try_pet_drop(uuid,text,text,text),public.phase5_pet_evolve(uuid,uuid,text),public.phase5_presence_touch(uuid),public.phase5_friend_request(uuid,uuid),public.phase5_friend_respond(uuid,uuid,boolean),public.phase5_friend_remove(uuid,uuid),public.phase5_chat_send(uuid,text,text),public.phase5_chat_mute(uuid,uuid,integer),public.phase5_chat_report(uuid,uuid,text),public.phase5_refresh_events(),public.phase5_event_bonus(text),public.phase5_event_eligible(uuid,text,timestamptz,timestamptz),public.phase5_claim_event(uuid,uuid,text),public.phase5_schedule_template(text,timestamptz,integer),public.phase5_sync_titles(uuid),public.phase5_set_title(uuid,text),public.phase5_sync_codex(uuid),public.phase5_refresh_rankings(),public.phase5_refresh_rankings_if_needed(),public.phase5_sync_notifications(uuid) from public,anon,authenticated;
grant execute on function public.phase5_rate_gate(uuid,text,integer,integer),public.phase5_pet_bonus(uuid,text),public.phase5_pet_equip(uuid,uuid),public.phase5_pet_add_xp(uuid,integer,text),public.phase5_try_pet_drop(uuid,text,text,text),public.phase5_pet_evolve(uuid,uuid,text),public.phase5_presence_touch(uuid),public.phase5_friend_request(uuid,uuid),public.phase5_friend_respond(uuid,uuid,boolean),public.phase5_friend_remove(uuid,uuid),public.phase5_chat_send(uuid,text,text),public.phase5_chat_mute(uuid,uuid,integer),public.phase5_chat_report(uuid,uuid,text),public.phase5_refresh_events(),public.phase5_event_bonus(text),public.phase5_event_eligible(uuid,text,timestamptz,timestamptz),public.phase5_claim_event(uuid,uuid,text),public.phase5_schedule_template(text,timestamptz,integer),public.phase5_sync_titles(uuid),public.phase5_set_title(uuid,text),public.phase5_sync_codex(uuid),public.phase5_refresh_rankings(),public.phase5_refresh_rankings_if_needed(),public.phase5_sync_notifications(uuid) to service_role;

commit;
