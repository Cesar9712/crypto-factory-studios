-- Nexus Realms Phase 2: server-authoritative procedural rifts + 1v1 arena.
-- Runtime game logic lives in supabase/functions/phase2-engine/index.ts.

create table if not exists public.phase2_rift_progress (
  character_id uuid primary key references public.characters(id) on delete cascade,
  highest_tier integer not null default 1 check (highest_tier between 1 and 50),
  runs_completed integer not null default 0 check (runs_completed >= 0),
  best_tier integer not null default 0 check (best_tier between 0 and 50),
  daily_runs integer not null default 0 check (daily_runs >= 0),
  daily_key date not null default current_date,
  updated_at timestamptz not null default now()
);

create table if not exists public.phase2_rift_runs (
  id uuid primary key default gen_random_uuid(),
  character_id uuid not null references public.characters(id) on delete cascade,
  seed text not null unique,
  tier integer not null check (tier between 1 and 50),
  difficulty text not null check (difficulty in ('normal','hard','nightmare','infernal')),
  modifier text not null,
  rooms jsonb not null check (jsonb_typeof(rooms)='array'),
  current_room integer not null default 0 check (current_room >= 0),
  status text not null default 'active' check (status in ('active','victory','defeat','abandoned')),
  energy_cost integer not null check (energy_cost > 0),
  current_hp integer not null,
  max_hp integer not null,
  current_mana integer not null,
  max_mana integer not null,
  total_gold bigint not null default 0,
  total_xp bigint not null default 0,
  total_essence bigint not null default 0,
  total_ore bigint not null default 0,
  total_wood bigint not null default 0,
  reward_item_id uuid references public.item_instances(id) on delete set null,
  last_resolution jsonb not null default '{}'::jsonb,
  started_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz
);
create unique index if not exists phase2_one_active_rift_per_character on public.phase2_rift_runs(character_id) where status='active';
create index if not exists phase2_rift_runs_character_recent on public.phase2_rift_runs(character_id,started_at desc);
create index if not exists phase2_rift_status_room_idx on public.phase2_rift_runs(character_id,status,current_room);

create table if not exists public.phase2_reward_events (
  event_key text primary key,
  character_id uuid not null references public.characters(id) on delete cascade,
  source text not null,
  rewards jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.phase2_arena_seasons (
  id text primary key,
  name text not null,
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  active boolean not null default false,
  created_at timestamptz not null default now(),
  check (ends_at > starts_at)
);
insert into public.phase2_arena_seasons(id,name,starts_at,ends_at,active)
values ('2026-09','Season of the First Rift','2026-09-01T00:00:00Z','2026-10-01T00:00:00Z',true)
on conflict(id) do update set name=excluded.name,starts_at=excluded.starts_at,ends_at=excluded.ends_at,active=excluded.active;

create table if not exists public.phase2_arena_profiles (
  character_id uuid primary key references public.characters(id) on delete cascade,
  season_id text not null references public.phase2_arena_seasons(id) on delete restrict,
  rating integer not null default 1000 check (rating between 0 and 5000),
  highest_rating integer not null default 1000 check (highest_rating between 0 and 5000),
  wins integer not null default 0 check (wins >= 0),
  losses integer not null default 0 check (losses >= 0),
  streak integer not null default 0,
  matches_today integer not null default 0 check (matches_today >= 0),
  matches_day date not null default current_date,
  last_match_at timestamptz,
  updated_at timestamptz not null default now()
);
create index if not exists phase2_arena_rating_idx on public.phase2_arena_profiles(season_id,rating desc);

create table if not exists public.phase2_arena_matches (
  id uuid primary key default gen_random_uuid(),
  season_id text not null references public.phase2_arena_seasons(id) on delete restrict,
  player_id uuid not null references public.characters(id) on delete cascade,
  opponent_id uuid not null references public.characters(id) on delete cascade,
  winner_id uuid not null references public.characters(id) on delete cascade,
  player_rating_before integer not null,
  player_rating_after integer not null,
  opponent_rating_before integer not null,
  opponent_rating_after integer not null,
  player_power integer not null,
  opponent_power integer not null,
  combat_log jsonb not null default '[]'::jsonb,
  request_key text not null unique,
  abuse_flags jsonb not null default '[]'::jsonb,
  reward_summary jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (player_id<>opponent_id),
  check (winner_id=player_id or winner_id=opponent_id)
);
create index if not exists phase2_arena_player_recent_idx on public.phase2_arena_matches(player_id,created_at desc);
create index if not exists phase2_arena_opponent_recent_idx on public.phase2_arena_matches(opponent_id,created_at desc);
create index if not exists phase2_arena_request_player_idx on public.phase2_arena_matches(request_key,player_id);

alter table public.phase2_rift_progress enable row level security;
alter table public.phase2_rift_runs enable row level security;
alter table public.phase2_reward_events enable row level security;
alter table public.phase2_arena_seasons enable row level security;
alter table public.phase2_arena_profiles enable row level security;
alter table public.phase2_arena_matches enable row level security;

create or replace function public.phase2_create_rift_run(p_character uuid,p_seed text,p_tier integer,p_difficulty text,p_modifier text,p_rooms jsonb,p_energy_cost integer)
returns jsonb language plpgsql security definer set search_path=public as $$
declare c public.characters%rowtype; prog public.phase2_rift_progress%rowtype; r public.phase2_rift_runs%rowtype;
begin
  if p_tier<1 or p_tier>50 then raise exception 'invalid_tier'; end if;
  if p_difficulty not in ('normal','hard','nightmare','infernal') then raise exception 'invalid_difficulty'; end if;
  if jsonb_typeof(p_rooms)<>'array' or jsonb_array_length(p_rooms)<5 then raise exception 'invalid_rooms'; end if;
  select * into c from public.characters where id=p_character for update;
  if not found then raise exception 'character_not_found'; end if;
  insert into public.phase2_rift_progress(character_id) values(p_character) on conflict(character_id) do nothing;
  select * into prog from public.phase2_rift_progress where character_id=p_character for update;
  if prog.daily_key<>current_date then update public.phase2_rift_progress set daily_key=current_date,daily_runs=0,updated_at=now() where character_id=p_character; prog.daily_runs:=0; end if;
  if prog.daily_runs>=8 then raise exception 'daily_rift_limit'; end if;
  if p_tier>prog.highest_tier then raise exception 'tier_locked'; end if;
  if p_difficulty='hard' and p_tier<2 then raise exception 'difficulty_locked'; end if;
  if p_difficulty='nightmare' and p_tier<4 then raise exception 'difficulty_locked'; end if;
  if p_difficulty='infernal' and p_tier<6 then raise exception 'difficulty_locked'; end if;
  if exists(select 1 from public.phase2_rift_runs where character_id=p_character and status='active') then raise exception 'rift_already_active'; end if;
  if c.energy<p_energy_cost then raise exception 'not_enough_energy'; end if;
  update public.characters set energy=energy-p_energy_cost,updated_at=now() where id=p_character;
  update public.phase2_rift_progress set daily_runs=daily_runs+1,updated_at=now() where character_id=p_character;
  insert into public.phase2_rift_runs(character_id,seed,tier,difficulty,modifier,rooms,energy_cost,current_hp,max_hp,current_mana,max_mana)
  values(p_character,p_seed,p_tier,p_difficulty,p_modifier,p_rooms,p_energy_cost,greatest(1,c.hp),c.max_hp,greatest(0,c.mana),c.max_mana) returning * into r;
  return to_jsonb(r);
end $$;

create or replace function public.phase2_apply_rift_rewards(p_character uuid,p_event_key text,p_gold bigint,p_xp bigint,p_essence bigint,p_ore bigint,p_wood bigint,p_item jsonb default null)
returns jsonb language plpgsql security definer set search_path=public as $$
declare inserted_key text; c public.characters%rowtype; cur_xp bigint; cur_level integer; gained integer:=0; new_item uuid:=null; rarity text; item_name text; item_atk integer; item_def integer; item_slot text;
begin
  insert into public.phase2_reward_events(event_key,character_id,source,rewards) values(p_event_key,p_character,'rift',jsonb_build_object('gold',p_gold,'xp',p_xp,'essence',p_essence,'ore',p_ore,'wood',p_wood,'item',p_item)) on conflict(event_key) do nothing returning event_key into inserted_key;
  if inserted_key is null then return jsonb_build_object('applied',false); end if;
  select * into c from public.characters where id=p_character for update;
  if not found then raise exception 'character_not_found'; end if;
  cur_xp:=c.xp+greatest(0,p_xp); cur_level:=c.level;
  while cur_xp>=cur_level*100 loop cur_xp:=cur_xp-cur_level*100;cur_level:=cur_level+1;gained:=gained+1; end loop;
  update public.characters set gold=gold+greatest(0,p_gold),xp=cur_xp,level=cur_level,max_hp=max_hp+12*gained,max_energy=max_energy+3*gained,max_mana=max_mana+5*gained,updated_at=now() where id=p_character;
  if gained>0 then update public.character_stats set atk=atk+2*gained,def=def+gained where character_id=p_character; end if;
  insert into public.resources(character_id,resource_key,amount) values(p_character,'essence',greatest(0,p_essence)) on conflict(character_id,resource_key) do update set amount=public.resources.amount+excluded.amount;
  insert into public.resources(character_id,resource_key,amount) values(p_character,'ore',greatest(0,p_ore)) on conflict(character_id,resource_key) do update set amount=public.resources.amount+excluded.amount;
  insert into public.resources(character_id,resource_key,amount) values(p_character,'wood',greatest(0,p_wood)) on conflict(character_id,resource_key) do update set amount=public.resources.amount+excluded.amount;
  if p_item is not null then
    rarity:=upper(coalesce(p_item->>'rarity','RARE')); if rarity not in ('COMMON','UNCOMMON','RARE','EPIC','LEGENDARY','MYTHIC') then rarity:='RARE'; end if;
    item_name:=left(coalesce(p_item->>'name','Riftbound Relic'),64); item_atk:=greatest(0,least(999,(coalesce(p_item->>'atk','0'))::integer)); item_def:=greatest(0,least(999,(coalesce(p_item->>'def','0'))::integer)); item_slot:=case when p_item->>'slot' in ('weapon','armor','boots','ring') then p_item->>'slot' else 'ring' end;
    insert into public.item_instances(owner_character_id,custom_name,rarity,atk,def,enhancement_level,metadata) values(p_character,item_name,rarity,item_atk,item_def,0,jsonb_build_object('type',item_slot,'slot',item_slot,'rift_exclusive',true,'source','unstable_rift','value',greatest(10,item_atk*4+item_def*3))) returning id into new_item;
  end if;
  return jsonb_build_object('applied',true,'item_id',new_item,'levels_gained',gained,'level',cur_level,'xp',cur_xp);
end $$;

create or replace function public.phase2_ensure_arena_profile(p_character uuid,p_season text)
returns jsonb language plpgsql security definer set search_path=public as $$
declare p public.phase2_arena_profiles%rowtype;
begin
  insert into public.phase2_arena_profiles(character_id,season_id) values(p_character,p_season) on conflict(character_id) do nothing;
  select * into p from public.phase2_arena_profiles where character_id=p_character for update;
  if p.season_id<>p_season then update public.phase2_arena_profiles set season_id=p_season,rating=1000,wins=0,losses=0,streak=0,matches_today=0,matches_day=current_date,last_match_at=null,updated_at=now() where character_id=p_character returning * into p; end if;
  if p.matches_day<>current_date then update public.phase2_arena_profiles set matches_day=current_date,matches_today=0,updated_at=now() where character_id=p_character returning * into p; end if;
  return to_jsonb(p);
end $$;

create or replace function public.phase2_record_arena_match(p_season text,p_player uuid,p_opponent uuid,p_winner uuid,p_player_power integer,p_opponent_power integer,p_log jsonb,p_request_key text)
returns jsonb language plpgsql security definer set search_path=public as $$
declare pp public.phase2_arena_profiles%rowtype; op public.phase2_arena_profiles%rowtype; pr integer; orating integer; pnew integer; onew integer; expected numeric; delta integer; pair_count integer; recent_count integer; winner_is_player boolean; match_id uuid; flags jsonb:='[]'::jsonb;
begin
  if p_player=p_opponent then raise exception 'self_match_forbidden'; end if;
  if p_winner<>p_player and p_winner<>p_opponent then raise exception 'invalid_winner'; end if;
  if exists(select 1 from public.phase2_arena_matches where request_key=p_request_key) then return (select jsonb_build_object('duplicate',true,'match_id',id,'player_rating',player_rating_after,'opponent_rating',opponent_rating_after) from public.phase2_arena_matches where request_key=p_request_key); end if;
  perform public.phase2_ensure_arena_profile(p_player,p_season); perform public.phase2_ensure_arena_profile(p_opponent,p_season);
  select * into pp from public.phase2_arena_profiles where character_id=p_player for update; select * into op from public.phase2_arena_profiles where character_id=p_opponent for update;
  if pp.matches_today>=25 then raise exception 'daily_arena_limit'; end if;
  if pp.last_match_at is not null and pp.last_match_at>now()-interval '20 seconds' then raise exception 'arena_cooldown'; end if;
  select count(*) into pair_count from public.phase2_arena_matches where created_at>=date_trunc('day',now()) and ((player_id=p_player and opponent_id=p_opponent) or (player_id=p_opponent and opponent_id=p_player));
  if pair_count>=3 then raise exception 'opponent_daily_limit'; end if;
  select count(*) into recent_count from public.phase2_arena_matches where created_at>now()-interval '10 minutes' and (player_id=p_player or opponent_id=p_player); if recent_count>=10 then raise exception 'arena_rate_limit'; end if;
  if pair_count>=2 then flags:=flags||jsonb_build_array('repeat_pair'); end if;
  pr:=pp.rating;orating:=op.rating;expected:=1.0/(1.0+power(10.0,(orating-pr)/400.0));winner_is_player:=p_winner=p_player;delta:=round(28*((case when winner_is_player then 1 else 0 end)-expected));if delta=0 then delta:=case when winner_is_player then 1 else -1 end; end if;pnew:=greatest(0,least(5000,pr+delta));onew:=greatest(0,least(5000,orating-delta));
  update public.phase2_arena_profiles set rating=pnew,highest_rating=greatest(highest_rating,pnew),wins=wins+(case when winner_is_player then 1 else 0 end),losses=losses+(case when winner_is_player then 0 else 1 end),streak=case when winner_is_player then greatest(1,streak+1) else least(-1,streak-1) end,matches_today=matches_today+1,last_match_at=now(),updated_at=now() where character_id=p_player;
  update public.phase2_arena_profiles set rating=onew,highest_rating=greatest(highest_rating,onew),wins=wins+(case when winner_is_player then 0 else 1 end),losses=losses+(case when winner_is_player then 1 else 0 end),streak=case when winner_is_player then least(-1,streak-1) else greatest(1,streak+1) end,matches_today=matches_today+1,last_match_at=now(),updated_at=now() where character_id=p_opponent;
  insert into public.phase2_arena_matches(season_id,player_id,opponent_id,winner_id,player_rating_before,player_rating_after,opponent_rating_before,opponent_rating_after,player_power,opponent_power,combat_log,request_key,abuse_flags) values(p_season,p_player,p_opponent,p_winner,pr,pnew,orating,onew,p_player_power,p_opponent_power,coalesce(p_log,'[]'::jsonb),p_request_key,flags) returning id into match_id;
  if winner_is_player then update public.characters set gold=gold+20 where id=p_player;update public.characters set gold=gold+8 where id=p_opponent;insert into public.resources(character_id,resource_key,amount) values(p_player,'essence',1) on conflict(character_id,resource_key) do update set amount=public.resources.amount+1;else update public.characters set gold=gold+8 where id=p_player;update public.characters set gold=gold+20 where id=p_opponent;insert into public.resources(character_id,resource_key,amount) values(p_opponent,'essence',1) on conflict(character_id,resource_key) do update set amount=public.resources.amount+1;end if;
  return jsonb_build_object('duplicate',false,'match_id',match_id,'player_rating_before',pr,'player_rating_after',pnew,'opponent_rating_before',orating,'opponent_rating_after',onew,'delta',pnew-pr,'abuse_flags',flags);
end $$;

revoke all on function public.phase2_create_rift_run(uuid,text,integer,text,text,jsonb,integer) from public,anon,authenticated;
revoke all on function public.phase2_apply_rift_rewards(uuid,text,bigint,bigint,bigint,bigint,bigint,jsonb) from public,anon,authenticated;
revoke all on function public.phase2_ensure_arena_profile(uuid,text) from public,anon,authenticated;
revoke all on function public.phase2_record_arena_match(text,uuid,uuid,uuid,integer,integer,jsonb,text) from public,anon,authenticated;
grant execute on function public.phase2_create_rift_run(uuid,text,integer,text,text,jsonb,integer) to service_role;
grant execute on function public.phase2_apply_rift_rewards(uuid,text,bigint,bigint,bigint,bigint,bigint,jsonb) to service_role;
grant execute on function public.phase2_ensure_arena_profile(uuid,text) to service_role;
grant execute on function public.phase2_record_arena_match(text,uuid,uuid,uuid,integer,integer,jsonb,text) to service_role;
