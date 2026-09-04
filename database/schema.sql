create extension if not exists pgcrypto;

create table if not exists profiles(
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique,
  username text unique not null,
  level int not null default 1,
  xp bigint not null default 0,
  gold bigint not null default 0,
  gems bigint not null default 0,
  energy int not null default 100,
  max_energy int not null default 100,
  hp int not null default 120,
  max_hp int not null default 120,
  created_at timestamptz not null default now()
);

create table if not exists wallets(
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references profiles(id) on delete cascade,
  chain_id int not null,
  address text not null,
  verified_at timestamptz,
  unique(chain_id,address)
);

create table if not exists item_definitions(
  id text primary key,
  name text not null,
  type text not null,
  slot text,
  rarity text not null,
  base_atk int not null default 0,
  base_def int not null default 0,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists item_instances(
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references profiles(id) on delete cascade,
  definition_id text references item_definitions(id),
  rarity text not null,
  atk int not null default 0,
  def int not null default 0,
  token_id numeric,
  contract_address text,
  equipped boolean not null default false,
  created_at timestamptz default now()
);

create table if not exists resources(
  profile_id uuid references profiles(id) on delete cascade,
  resource_key text,
  amount bigint not null default 0,
  primary key(profile_id,resource_key)
);

create table if not exists quests(
  id text primary key,
  name text not null,
  kind text not null,
  target int not null,
  reward jsonb not null
);

create table if not exists quest_progress(
  profile_id uuid references profiles(id) on delete cascade,
  quest_id text references quests(id) on delete cascade,
  progress int not null default 0,
  claimed_at timestamptz,
  primary key(profile_id,quest_id)
);

create table if not exists marketplace_listings(
  id uuid primary key default gen_random_uuid(),
  seller_id uuid references profiles(id),
  item_instance_id uuid references item_instances(id),
  price numeric(30,0) not null check(price>0),
  status text not null default 'active',
  created_at timestamptz default now()
);
create index if not exists market_status_price_idx on marketplace_listings(status,price);

create table if not exists game_transactions(
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references profiles(id),
  kind text not null,
  delta jsonb not null,
  chain_tx_hash text,
  created_at timestamptz default now()
);

create table if not exists guilds(
  id uuid primary key default gen_random_uuid(),
  name text unique not null,
  level int not null default 1,
  treasury bigint not null default 0
);

create table if not exists guild_members(
  guild_id uuid references guilds(id) on delete cascade,
  profile_id uuid references profiles(id) on delete cascade,
  role text not null default 'member',
  primary key(guild_id,profile_id)
);

-- Before production: bind profiles.auth_user_id to auth.users(id), enable RLS,
-- and create policies that never allow clients to mutate authoritative currency,
-- XP, loot, inventory ownership, or marketplace settlement directly.
