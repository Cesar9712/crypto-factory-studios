create table if not exists public.manual_combat_sessions (
  id uuid primary key default gen_random_uuid(),
  character_id uuid not null references public.characters(id) on delete cascade,
  enemy_id text not null references public.enemy_definitions(id),
  status text not null default 'active' check (status in ('active','victory','defeat','fled','expired')),
  turn integer not null default 0 check (turn >= 0 and turn <= 100),
  player_hp integer not null check (player_hp >= 0),
  player_mana integer not null check (player_mana >= 0),
  enemy_hp integer not null check (enemy_hp >= 0),
  cooldowns jsonb not null default '{}'::jsonb,
  guard_reduction numeric(6,3) not null default 1,
  energy_cost integer not null default 0 check (energy_cost >= 0),
  marked boolean not null default false,
  combat_log jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '20 minutes')
);
create unique index if not exists manual_combat_one_active_per_character on public.manual_combat_sessions(character_id) where status='active';
create index if not exists manual_combat_sessions_character_updated_idx on public.manual_combat_sessions(character_id, updated_at desc);
alter table public.manual_combat_sessions enable row level security;
revoke all on public.manual_combat_sessions from anon, authenticated;
grant all on public.manual_combat_sessions to service_role;
alter table public.combat_history add column if not exists manual_session_id uuid references public.manual_combat_sessions(id) on delete set null;
create unique index if not exists combat_history_manual_session_uidx on public.combat_history(manual_session_id) where manual_session_id is not null;
