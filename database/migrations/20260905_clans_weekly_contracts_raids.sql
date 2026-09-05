-- Clan social progression: levels, weekly contracts, shared raid boss and server-authoritative contributions.
alter table public.guilds
  add column if not exists tag text,
  add column if not exists description text not null default '',
  add column if not exists xp bigint not null default 0,
  add column if not exists is_open boolean not null default true,
  add column if not exists max_members integer not null default 20,
  add column if not exists owner_character_id uuid references public.characters(id) on delete set null,
  add column if not exists updated_at timestamptz not null default now();
alter table public.guild_members
  add column if not exists contribution_points bigint not null default 0,
  add column if not exists weekly_points bigint not null default 0;
create unique index if not exists guild_members_one_guild_per_character on public.guild_members(character_id);
create unique index if not exists guilds_tag_unique on public.guilds(lower(tag)) where tag is not null;

create table if not exists public.guild_weekly_progress (
 guild_id uuid not null references public.guilds(id) on delete cascade,
 week_start date not null, combat integer not null default 0, gather integer not null default 0,
 craft integer not null default 0, expedition integer not null default 0, boss integer not null default 0,
 updated_at timestamptz not null default now(), primary key(guild_id,week_start));
create table if not exists public.guild_weekly_claims (
 guild_id uuid not null references public.guilds(id) on delete cascade,
 character_id uuid not null references public.characters(id) on delete cascade,
 week_start date not null, claimed_at timestamptz not null default now(), primary key(guild_id,character_id,week_start));
create table if not exists public.guild_raids (
 guild_id uuid not null references public.guilds(id) on delete cascade, week_start date not null,
 boss_name text not null default 'Abyss Herald', max_hp bigint not null, current_hp bigint not null,
 status text not null default 'active' check(status in ('active','defeated','expired')),
 created_at timestamptz not null default now(), updated_at timestamptz not null default now(), primary key(guild_id,week_start));
create table if not exists public.guild_raid_contributions (
 guild_id uuid not null references public.guilds(id) on delete cascade, week_start date not null,
 character_id uuid not null references public.characters(id) on delete cascade, damage bigint not null default 0,
 attempts integer not null default 0, claimed_at timestamptz, updated_at timestamptz not null default now(),
 primary key(guild_id,week_start,character_id), foreign key(guild_id,week_start) references public.guild_raids(guild_id,week_start) on delete cascade);
create table if not exists public.guild_activity (
 id uuid primary key default gen_random_uuid(), guild_id uuid not null references public.guilds(id) on delete cascade,
 character_id uuid references public.characters(id) on delete set null, kind text not null, amount integer not null default 1,
 metadata jsonb not null default '{}'::jsonb, created_at timestamptz not null default now());

alter table public.guild_weekly_progress enable row level security;
alter table public.guild_weekly_claims enable row level security;
alter table public.guild_raids enable row level security;
alter table public.guild_raid_contributions enable row level security;
alter table public.guild_activity enable row level security;

create or replace function public.current_game_week() returns date language sql stable as $$select date_trunc('week',timezone('utc',now()))::date$$;

-- Operational functions and triggers are intentionally server-side. They are deployed in Supabase and exposed only to service_role through clan-engine.
-- They create/join/leave clans atomically, track clan XP from combat/gather/craft/expedition logs,
-- calculate weekly contract targets, distribute internal rewards, and run the shared weekly clan raid.
