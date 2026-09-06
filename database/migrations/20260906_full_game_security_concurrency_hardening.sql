begin;

-- Global audit hardening: keep privileged game mutations behind authenticated Edge Functions.
revoke all on function public.phase3_award_set_drop(uuid,text,integer,boolean) from public,anon,authenticated;
revoke all on function public.phase3_build_profile(uuid,boolean) from public,anon,authenticated;
revoke all on function public.phase3_equip_item(uuid,uuid) from public,anon,authenticated;
revoke all on function public.phase3_set_specialization(uuid,text) from public,anon,authenticated;
revoke all on function public.phase3_unequip_slot(uuid,text) from public,anon,authenticated;
revoke all on function public.phase4_bastion_craft_benefit() from public,anon,authenticated;

grant execute on function public.phase3_award_set_drop(uuid,text,integer,boolean) to service_role;
grant execute on function public.phase3_build_profile(uuid,boolean) to service_role;
grant execute on function public.phase3_equip_item(uuid,uuid) to service_role;
grant execute on function public.phase3_set_specialization(uuid,text) to service_role;
grant execute on function public.phase3_unequip_slot(uuid,text) to service_role;
grant execute on function public.phase4_bastion_craft_benefit() to service_role;

alter function public.phase3_effect_add(jsonb,jsonb) set search_path=public;

-- Short-lived leases serialize expensive one-shot actions such as automatic combat.
create table if not exists public.game_action_leases(
  character_id uuid not null references public.characters(id) on delete cascade,
  action_key text not null check(char_length(action_key) between 1 and 48),
  request_key text not null check(char_length(request_key) between 1 and 128),
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key(character_id,action_key)
);
create index if not exists ix_game_action_leases_expiry on public.game_action_leases(expires_at);
alter table public.game_action_leases enable row level security;
revoke all on public.game_action_leases from public,anon,authenticated;
grant all on public.game_action_leases to service_role;

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
  return v_acquired=v_request;
end$$;

create or replace function public.fullgame_release_action_lease(
  p_character uuid,
  p_action text,
  p_request text
) returns boolean
language plpgsql
security definer
set search_path=public
as $$
declare v_deleted integer;
begin
  delete from public.game_action_leases
   where character_id=p_character and action_key=p_action and request_key=p_request;
  get diagnostics v_deleted=row_count;
  return v_deleted>0;
end$$;

-- Regeneration is calculated from the locked server row so simultaneous state refreshes cannot overwrite combat state.
create or replace function public.fullgame_regen_character(p_character uuid)
returns jsonb
language plpgsql
security definer
set search_path=public
as $$
declare
  c public.characters%rowtype;
  v_minutes integer;
  v_boost_minutes integer:=0;
  v_effective_minutes integer;
  v_energy_rate integer;
  v_hp_rate integer;
  v_mana_rate integer;
  v_last timestamptz;
begin
  select * into c from public.characters where id=p_character for update;
  if not found then raise exception 'Character not found'; end if;
  v_last:=coalesce(c.last_tick,c.updated_at,c.created_at,now());
  v_minutes:=greatest(0,floor(extract(epoch from(now()-v_last))/60)::integer);
  if v_minutes<=0 then return to_jsonb(c); end if;

  if c.regen_boost_until is not null and c.regen_boost_until>v_last then
    v_boost_minutes:=least(v_minutes,greatest(0,ceil(extract(epoch from(c.regen_boost_until-v_last))/60)::integer));
  end if;
  v_effective_minutes:=v_minutes+v_boost_minutes;
  if c.location='bastion' or c.zone_id='bastion' then
    v_energy_rate:=2;
    v_hp_rate:=greatest(1,ceil(c.max_hp*0.03)::integer);
    v_mana_rate:=5;
  else
    v_energy_rate:=1;
    v_hp_rate:=greatest(1,ceil(c.max_hp*0.01)::integer);
    v_mana_rate:=2;
  end if;

  update public.characters
     set energy=least(max_energy,energy+v_energy_rate*v_effective_minutes),
         hp=least(max_hp,hp+v_hp_rate*v_effective_minutes),
         mana=least(max_mana,mana+v_mana_rate*v_effective_minutes),
         last_tick=v_last+v_minutes*interval '1 minute',
         updated_at=now()
   where id=p_character
   returning * into c;
  return to_jsonb(c);
end$$;

-- Energy consumption rechecks the latest locked row after regeneration.
create or replace function public.fullgame_consume_energy(p_character uuid,p_amount integer)
returns jsonb
language plpgsql
security definer
set search_path=public
as $$
declare c public.characters%rowtype;
begin
  if p_amount is null or p_amount<=0 or p_amount>100000 then raise exception 'Invalid energy amount'; end if;
  perform public.fullgame_regen_character(p_character);
  select * into c from public.characters where id=p_character for update;
  if not found then raise exception 'Character not found'; end if;
  if c.energy<p_amount then raise exception 'Not enough energy: need %',p_amount; end if;
  update public.characters set energy=energy-p_amount,updated_at=now() where id=p_character returning * into c;
  return to_jsonb(c);
end$$;

-- Additive combat rewards and level progression are serialized on the character row.
create or replace function public.fullgame_apply_character_progress(
  p_character uuid,
  p_gold bigint default 0,
  p_xp bigint default 0,
  p_renown integer default 0,
  p_hp integer default null,
  p_mana integer default null,
  p_location text default null,
  p_zone text default null
) returns jsonb
language plpgsql
security definer
set search_path=public
as $$
declare
  c public.characters%rowtype;
  v_xp bigint;
  v_level integer;
  v_gained integer:=0;
  v_new_max_hp integer;
  v_new_max_mana integer;
begin
  if coalesce(p_gold,0)<0 or coalesce(p_xp,0)<0 or coalesce(p_renown,0)<0 then raise exception 'Negative progression delta'; end if;
  select * into c from public.characters where id=p_character for update;
  if not found then raise exception 'Character not found'; end if;

  v_xp:=c.xp+coalesce(p_xp,0);
  v_level:=c.level;
  while v_xp>=v_level*100 loop
    v_xp:=v_xp-v_level*100;
    v_level:=v_level+1;
    v_gained:=v_gained+1;
    if v_level>=1000 then exit; end if;
  end loop;
  v_new_max_hp:=c.max_hp+12*v_gained;
  v_new_max_mana:=c.max_mana+5*v_gained;

  update public.characters
     set gold=gold+coalesce(p_gold,0),
         renown=renown+coalesce(p_renown,0),
         xp=v_xp,
         level=v_level,
         max_hp=v_new_max_hp,
         max_energy=max_energy+3*v_gained,
         max_mana=v_new_max_mana,
         hp=case when p_hp is null then hp else least(v_new_max_hp,greatest(0,p_hp)) end,
         mana=case when p_mana is null then mana else least(v_new_max_mana,greatest(0,p_mana)) end,
         location=coalesce(p_location,location),
         zone_id=coalesce(p_zone,zone_id),
         updated_at=now()
   where id=p_character
   returning * into c;

  if v_gained>0 then
    update public.character_stats set atk=atk+2*v_gained,def=def+v_gained where character_id=p_character;
  end if;
  return to_jsonb(c)||jsonb_build_object('levels_gained',v_gained);
end$$;

-- Attribute allocation is one atomic transaction, including derived HP/mana capacity changes.
create or replace function public.fullgame_allocate_stat(p_character uuid,p_stat text)
returns jsonb
language plpgsql
security definer
set search_path=public
as $$
declare s public.character_stats%rowtype;
declare c public.characters%rowtype;
begin
  if p_stat not in('strength','vitality','agility','intelligence','luck') then raise exception 'Unknown attribute'; end if;
  select * into c from public.characters where id=p_character for update;
  if not found then raise exception 'Character not found'; end if;
  select * into s from public.character_stats where character_id=p_character for update;
  if not found then raise exception 'Character stats not found'; end if;
  if s.unspent_points<=0 then raise exception 'No stat points available'; end if;

  update public.character_stats
     set strength=strength+case when p_stat='strength' then 1 else 0 end,
         vitality=vitality+case when p_stat='vitality' then 1 else 0 end,
         agility=agility+case when p_stat='agility' then 1 else 0 end,
         intelligence=intelligence+case when p_stat='intelligence' then 1 else 0 end,
         luck=luck+case when p_stat='luck' then 1 else 0 end,
         unspent_points=unspent_points-1
   where character_id=p_character
   returning * into s;

  if p_stat='vitality' then
    update public.characters set max_hp=max_hp+3,hp=least(max_hp+3,hp+3),updated_at=now() where id=p_character returning * into c;
  elsif p_stat='intelligence' then
    update public.characters set max_mana=max_mana+2,mana=least(max_mana+2,mana+2),updated_at=now() where id=p_character returning * into c;
  end if;
  return jsonb_build_object('stat',p_stat,'value',case p_stat when 'strength' then s.strength when 'vitality' then s.vitality when 'agility' then s.agility when 'intelligence' then s.intelligence else s.luck end,'unspent_points',s.unspent_points,'max_hp',c.max_hp,'max_mana',c.max_mana);
end$$;

revoke all on function public.fullgame_acquire_action_lease(uuid,text,text,integer),public.fullgame_release_action_lease(uuid,text,text),public.fullgame_regen_character(uuid),public.fullgame_consume_energy(uuid,integer),public.fullgame_apply_character_progress(uuid,bigint,bigint,integer,integer,integer,text,text),public.fullgame_allocate_stat(uuid,text) from public,anon,authenticated;
grant execute on function public.fullgame_acquire_action_lease(uuid,text,text,integer),public.fullgame_release_action_lease(uuid,text,text),public.fullgame_regen_character(uuid),public.fullgame_consume_energy(uuid,integer),public.fullgame_apply_character_progress(uuid,bigint,bigint,integer,integer,integer,text,text),public.fullgame_allocate_stat(uuid,text) to service_role;

commit;
