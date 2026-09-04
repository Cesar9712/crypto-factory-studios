-- Web3/MMO-inspired gameplay progression. In-game only: no real-money settlement.

alter table public.characters add column if not exists renown integer not null default 0;
alter table public.item_instances add column if not exists enhancement_level integer not null default 0;

create table if not exists public.profession_progress (
  character_id uuid not null references public.characters(id) on delete cascade,
  profession_key text not null check (profession_key in ('mining','woodcutting','fishing','smithing')),
  level integer not null default 1 check (level between 1 and 100),
  xp integer not null default 0 check (xp >= 0),
  updated_at timestamptz not null default now(),
  primary key (character_id, profession_key)
);

create table if not exists public.monster_codex (
  character_id uuid not null references public.characters(id) on delete cascade,
  enemy_id text not null references public.enemy_definitions(id) on delete cascade,
  kills integer not null default 0 check (kills >= 0),
  claimed_tier integer not null default 0 check (claimed_tier between 0 and 3),
  updated_at timestamptz not null default now(),
  primary key (character_id, enemy_id)
);

create table if not exists public.daily_bounties (
  character_id uuid not null references public.characters(id) on delete cascade,
  bounty_date date not null,
  bounty_key text not null,
  progress integer not null default 0 check (progress >= 0),
  target integer not null check (target > 0),
  reward_gold integer not null default 0 check (reward_gold >= 0),
  reward_xp integer not null default 0 check (reward_xp >= 0),
  claimed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  primary key (character_id, bounty_date, bounty_key)
);

create table if not exists public.expedition_definitions (
  id text primary key,
  name text not null,
  required_level integer not null default 1,
  energy_cost integer not null default 20,
  difficulty integer not null default 1,
  waves integer not null default 3,
  reward_gold integer not null default 50,
  reward_xp integer not null default 50,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.expedition_runs (
  id uuid primary key default gen_random_uuid(),
  character_id uuid not null references public.characters(id) on delete cascade,
  expedition_id text not null references public.expedition_definitions(id),
  victory boolean not null,
  score integer not null default 0,
  rewards jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.world_events (
  id text primary key,
  name text not null,
  max_hp bigint not null check (max_hp > 0),
  current_hp bigint not null check (current_hp >= 0),
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  status text not null default 'active' check (status in ('active','defeated','expired')),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.world_event_contributions (
  event_id text not null references public.world_events(id) on delete cascade,
  character_id uuid not null references public.characters(id) on delete cascade,
  damage bigint not null default 0 check (damage >= 0),
  attempts integer not null default 0 check (attempts >= 0),
  claimed_at timestamptz,
  updated_at timestamptz not null default now(),
  primary key (event_id, character_id)
);

insert into public.expedition_definitions (id,name,required_level,energy_cost,difficulty,waves,reward_gold,reward_xp,metadata) values
('ember-vault','Ember Vault',2,18,1,3,70,60,'{"name_es":"Cripta de Ascuas","description_en":"A short three-wave dungeon with volatile creatures and a guardian cache.","description_es":"Una mazmorra corta de tres oleadas con criaturas volátiles y un alijo del guardián."}'::jsonb),
('sunken-halls','Sunken Halls',5,24,2,4,145,120,'{"name_es":"Salones Hundidos","description_en":"Flooded ruins with tougher waves and better essence rewards.","description_es":"Ruinas inundadas con oleadas más duras y mejores recompensas de esencia."}'::jsonb),
('frost-labyrinth','Frost Labyrinth',8,31,3,5,250,205,'{"name_es":"Laberinto de Escarcha","description_en":"A long expedition where preparation and gear power matter.","description_es":"Una expedición larga donde importan la preparación y el poder del equipo."}'::jsonb),
('rift-citadel','Rift Citadel',12,40,4,6,430,350,'{"name_es":"Ciudadela de la Grieta","description_en":"Endgame expedition with elite waves and high-tier loot chances.","description_es":"Expedición de alto nivel con élites y mejores probabilidades de botín."}'::jsonb)
on conflict (id) do update set
  name=excluded.name,
  required_level=excluded.required_level,
  energy_cost=excluded.energy_cost,
  difficulty=excluded.difficulty,
  waves=excluded.waves,
  reward_gold=excluded.reward_gold,
  reward_xp=excluded.reward_xp,
  metadata=excluded.metadata;

create or replace function public.damage_world_event(p_event_id text, p_character_id uuid, p_damage bigint)
returns table(current_hp bigint, applied_damage bigint)
language plpgsql
security definer
set search_path = public
as $$
declare
  before_hp bigint;
  dealt bigint;
begin
  select we.current_hp into before_hp
  from public.world_events as we
  where we.id=p_event_id and we.status='active'
  for update;
  if before_hp is null then raise exception 'world_event_not_active'; end if;
  dealt := least(greatest(p_damage,0), before_hp);
  update public.world_events as we
    set current_hp=greatest(0,we.current_hp-dealt),
        status=case when we.current_hp-dealt<=0 then 'defeated' else we.status end
    where we.id=p_event_id
    returning we.current_hp into current_hp;
  insert into public.world_event_contributions(event_id,character_id,damage,attempts,updated_at)
  values(p_event_id,p_character_id,dealt,1,now())
  on conflict(event_id,character_id) do update
    set damage=world_event_contributions.damage+excluded.damage,
        attempts=world_event_contributions.attempts+1,
        updated_at=now();
  applied_damage := dealt;
  return next;
end;
$$;

revoke all on function public.damage_world_event(text, uuid, bigint) from public;
revoke all on function public.damage_world_event(text, uuid, bigint) from anon;
revoke all on function public.damage_world_event(text, uuid, bigint) from authenticated;
grant execute on function public.damage_world_event(text, uuid, bigint) to service_role;

alter table public.profession_progress enable row level security;
alter table public.monster_codex enable row level security;
alter table public.daily_bounties enable row level security;
alter table public.expedition_definitions enable row level security;
alter table public.expedition_runs enable row level security;
alter table public.world_events enable row level security;
alter table public.world_event_contributions enable row level security;
