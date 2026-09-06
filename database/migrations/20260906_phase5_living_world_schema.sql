begin;

create table if not exists public.pet_definitions(
  pet_key text primary key,
  name_es text not null,
  name_en text not null,
  rarity text not null check(rarity in ('common','uncommon','rare','epic','legendary','mythic')),
  passive_key text not null check(passive_key in ('gathering','xp','boss_damage','crafting','collection')),
  passive_percent numeric(6,4) not null default 0 check(passive_percent>=0 and passive_percent<=0.02),
  appearance text not null,
  origin text not null,
  evolvable boolean not null default true,
  evolution_level integer not null default 20 check(evolution_level>=1),
  evolution_resource_key text not null default 'essence',
  evolution_resource_amount integer not null default 80 check(evolution_resource_amount>=0),
  evolution_item_id text not null default 'pet_evolution_core',
  max_level integer not null default 50 check(max_level between 1 and 100),
  enabled boolean not null default true,
  created_at timestamptz not null default now()
);

insert into public.pet_definitions(pet_key,name_es,name_en,rarity,passive_key,passive_percent,appearance,origin,evolution_level,evolution_resource_key,evolution_resource_amount) values
 ('ash_wolf','Lobo de Ceniza','Ash Wolf','rare','boss_damage',0.02,'🐺','Bosses de clan',20,'ore',90),
 ('astral_fox','Zorro Astral','Astral Fox','epic','xp',0.02,'🦊','Misiones y colecciones',20,'essence',80),
 ('rift_hawk','Halcón de Grieta','Rift Hawk','rare','gathering',0.02,'🦅','Grietas y eventos',20,'essence',75),
 ('ancient_spirit','Espíritu Antiguo','Ancient Spirit','legendary','crafting',0.02,'👻','Códice y colecciones',25,'wood',120),
 ('draconid','Dracónido','Draconid','mythic','collection',0.01,'🐲','World Boss y eventos especiales',30,'essence',160)
on conflict(pet_key) do update set name_es=excluded.name_es,name_en=excluded.name_en,rarity=excluded.rarity,passive_key=excluded.passive_key,passive_percent=excluded.passive_percent,appearance=excluded.appearance,origin=excluded.origin,evolvable=excluded.evolvable,evolution_level=excluded.evolution_level,evolution_resource_key=excluded.evolution_resource_key,evolution_resource_amount=excluded.evolution_resource_amount,evolution_item_id=excluded.evolution_item_id,max_level=excluded.max_level,enabled=excluded.enabled;

insert into public.item_definitions(id,name,type,slot,rarity,base_atk,base_def,base_value,metadata)
values('pet_evolution_core','Núcleo de Evolución','material',null,'epic',0,0,250,'{"phase":5,"petEvolution":true}'::jsonb)
on conflict(id) do nothing;

create table if not exists public.character_pets(
  id uuid primary key default gen_random_uuid(),
  character_id uuid not null references public.characters(id) on delete cascade,
  pet_key text not null references public.pet_definitions(pet_key),
  level integer not null default 1 check(level between 1 and 100),
  xp bigint not null default 0 check(xp>=0),
  evolution_stage integer not null default 0 check(evolution_stage between 0 and 5),
  equipped boolean not null default false,
  acquired_from text not null default 'unknown',
  acquired_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(character_id,pet_key)
);
create unique index if not exists ux_character_pets_one_equipped on public.character_pets(character_id) where equipped;
create index if not exists ix_character_pets_character on public.character_pets(character_id,level desc);

create table if not exists public.phase5_action_receipts(
  receipt_key text primary key,
  character_id uuid references public.characters(id) on delete cascade,
  action_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists ix_phase5_receipts_character on public.phase5_action_receipts(character_id,created_at desc);

create table if not exists public.pet_bonus_bank(
  character_id uuid not null references public.characters(id) on delete cascade,
  bonus_key text not null,
  resource_key text not null,
  amount numeric(18,6) not null default 0,
  updated_at timestamptz not null default now(),
  primary key(character_id,bonus_key,resource_key)
);

create table if not exists public.friend_requests(
  id uuid primary key default gen_random_uuid(),
  requester_id uuid not null references public.characters(id) on delete cascade,
  addressee_id uuid not null references public.characters(id) on delete cascade,
  status text not null default 'pending' check(status in ('pending','accepted','declined','cancelled')),
  created_at timestamptz not null default now(),
  responded_at timestamptz,
  check(requester_id<>addressee_id)
);
create unique index if not exists ux_friend_pending_pair on public.friend_requests(requester_id,addressee_id) where status='pending';
create index if not exists ix_friend_requests_addressee on public.friend_requests(addressee_id,status,created_at desc);

create table if not exists public.friendships(
  character_a uuid not null references public.characters(id) on delete cascade,
  character_b uuid not null references public.characters(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key(character_a,character_b),
  check(character_a<>character_b)
);

create table if not exists public.player_presence(
  character_id uuid primary key references public.characters(id) on delete cascade,
  status text not null default 'online' check(status in ('online','away','offline')),
  last_seen_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.chat_messages(
  id uuid primary key default gen_random_uuid(),
  character_id uuid not null references public.characters(id) on delete cascade,
  channel text not null check(channel in ('global','clan')),
  guild_id uuid references public.guilds(id) on delete cascade,
  body text not null check(char_length(body) between 1 and 280),
  created_at timestamptz not null default now(),
  check((channel='global' and guild_id is null) or (channel='clan' and guild_id is not null))
);
create index if not exists ix_chat_messages_global on public.chat_messages(channel,created_at desc);
create index if not exists ix_chat_messages_clan on public.chat_messages(guild_id,created_at desc) where channel='clan';

create table if not exists public.chat_mutes(
  muter_character_id uuid not null references public.characters(id) on delete cascade,
  muted_character_id uuid not null references public.characters(id) on delete cascade,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  primary key(muter_character_id,muted_character_id),
  check(muter_character_id<>muted_character_id)
);

create table if not exists public.chat_reports(
  id uuid primary key default gen_random_uuid(),
  reporter_character_id uuid not null references public.characters(id) on delete cascade,
  message_id uuid not null references public.chat_messages(id) on delete cascade,
  reason text not null check(char_length(reason) between 3 and 240),
  created_at timestamptz not null default now(),
  unique(reporter_character_id,message_id)
);

create table if not exists public.phase5_rate_events(
  id bigserial primary key,
  character_id uuid not null references public.characters(id) on delete cascade,
  bucket text not null,
  created_at timestamptz not null default now()
);
create index if not exists ix_phase5_rate on public.phase5_rate_events(character_id,bucket,created_at desc);

create table if not exists public.title_definitions(
  title_key text primary key,
  name_es text not null,
  name_en text not null,
  requirement_type text not null,
  requirement_value bigint not null default 1,
  description_es text not null,
  description_en text not null,
  enabled boolean not null default true
);
insert into public.title_definitions values
 ('dragon_slayer','Matadragones','Dragon Slayer','boss_damage',5000,'Inflige gran daño a bosses.','Deal major damage to bosses.',true),
 ('master_smith','Maestro Herrero','Master Smith','smithing_level',10,'Domina la profesión de Herrería.','Master the Smithing profession.',true),
 ('immortal','Inmortal','Immortal','level',25,'Alcanza un nivel de veterano.','Reach veteran level.',true),
 ('rift_lord','Señor de la Grieta','Lord of the Rift','rift_tier',5,'Supera Grietas de alto nivel.','Clear high-tier Rifts.',true),
 ('arena_champion','Campeón de Arena','Arena Champion','arena_rating',1200,'Alcanza una gran clasificación en Arena.','Reach a high Arena rating.',true)
on conflict(title_key) do update set name_es=excluded.name_es,name_en=excluded.name_en,requirement_type=excluded.requirement_type,requirement_value=excluded.requirement_value,description_es=excluded.description_es,description_en=excluded.description_en,enabled=excluded.enabled;

create table if not exists public.character_titles(
  character_id uuid not null references public.characters(id) on delete cascade,
  title_key text not null references public.title_definitions(title_key),
  unlocked_at timestamptz not null default now(),
  primary key(character_id,title_key)
);
alter table public.characters add column if not exists selected_title_key text;

create table if not exists public.phase5_weekly_event_definitions(
  event_key text primary key,
  weekday smallint not null check(weekday between 1 and 7),
  name_es text not null,
  name_en text not null,
  event_type text not null,
  bonus_key text,
  bonus_percent numeric(6,4) not null default 0 check(bonus_percent between 0 and 0.50),
  reward jsonb not null default '{}'::jsonb,
  enabled boolean not null default true,
  config jsonb not null default '{}'::jsonb
);
insert into public.phase5_weekly_event_definitions(event_key,weekday,name_es,name_en,event_type,bonus_key,bonus_percent,reward) values
 ('clan_boss_monday',1,'Lunes: Boss de Clan','Monday: Clan Boss','clan_boss',null,0,'{"gold":50}'::jsonb),
 ('gathering_tuesday',2,'Martes: Gathering Bonus','Tuesday: Gathering Bonus','gathering','gathering',0.10,'{"gold":40}'::jsonb),
 ('arena_wednesday',3,'Miércoles: Arena','Wednesday: Arena','arena','arena',0.05,'{"gold":60}'::jsonb),
 ('rift_thursday',4,'Jueves: Grietas','Thursday: Rifts','rift','rift',0.05,'{"gold":55,"evolution_core":1}'::jsonb),
 ('world_event_friday',5,'Viernes: Evento Mundial','Friday: World Event','world_event',null,0,'{"gold":60}'::jsonb),
 ('clan_wars_saturday',6,'Sábado: Clan Wars','Saturday: Clan Wars','clan_war',null,0,'{"gold":70}'::jsonb),
 ('world_boss_sunday',7,'Domingo: World Boss','Sunday: World Boss','world_boss','boss_damage',0.05,'{"gold":75}'::jsonb)
on conflict(event_key) do update set weekday=excluded.weekday,name_es=excluded.name_es,name_en=excluded.name_en,event_type=excluded.event_type,bonus_key=excluded.bonus_key,bonus_percent=excluded.bonus_percent,reward=excluded.reward,enabled=true;

create table if not exists public.phase5_event_templates(
  template_key text primary key,
  name_es text not null,
  name_en text not null,
  theme text not null,
  default_duration_hours integer not null default 168,
  config jsonb not null default '{}'::jsonb,
  enabled boolean not null default true
);
insert into public.phase5_event_templates values
 ('halloween','Halloween','Halloween','halloween',168,'{"temporary":true}'::jsonb,true),
 ('winter','Invierno','Winter','winter',336,'{"temporary":true}'::jsonb,true),
 ('anniversary','Aniversario','Anniversary','anniversary',168,'{"temporary":true}'::jsonb,true),
 ('rift_season','Temporada de Grietas','Rift Season','rift',336,'{"temporary":true}'::jsonb,true)
on conflict(template_key) do update set name_es=excluded.name_es,name_en=excluded.name_en,theme=excluded.theme,default_duration_hours=excluded.default_duration_hours,config=excluded.config,enabled=excluded.enabled;

create table if not exists public.phase5_event_instances(
  id uuid primary key default gen_random_uuid(),
  event_key text not null,
  template_key text references public.phase5_event_templates(template_key),
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  status text not null default 'scheduled' check(status in ('scheduled','active','ended','cancelled')),
  reward jsonb not null default '{}'::jsonb,
  config jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(event_key,starts_at)
);
create index if not exists ix_phase5_events_time on public.phase5_event_instances(starts_at,ends_at,status);

create table if not exists public.phase5_event_claims(
  event_instance_id uuid not null references public.phase5_event_instances(id) on delete cascade,
  character_id uuid not null references public.characters(id) on delete cascade,
  reward jsonb not null default '{}'::jsonb,
  claimed_at timestamptz not null default now(),
  primary key(event_instance_id,character_id)
);

create table if not exists public.player_notifications(
  id uuid primary key default gen_random_uuid(),
  character_id uuid not null references public.characters(id) on delete cascade,
  kind text not null,
  title text not null,
  body text not null,
  dedupe_key text not null,
  read_at timestamptz,
  created_at timestamptz not null default now(),
  unique(character_id,dedupe_key)
);
create index if not exists ix_notifications_character on public.player_notifications(character_id,read_at,created_at desc);

create table if not exists public.phase5_rankings(
  ranking_key text not null,
  entity_type text not null check(entity_type in ('character','guild')),
  entity_id uuid not null,
  score numeric not null,
  rank integer not null,
  snapshot_at timestamptz not null default now(),
  primary key(ranking_key,entity_id)
);
create index if not exists ix_phase5_rankings_key on public.phase5_rankings(ranking_key,rank);

create table if not exists public.phase5_meta(
  meta_key text primary key,
  value jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.phase5_codex_catalog(
  category text not null check(category in ('monsters','bosses','equipment','sets','pets','resources','zones')),
  entry_key text not null,
  name_es text not null,
  name_en text not null,
  icon text not null default '✦',
  source text not null,
  metadata jsonb not null default '{}'::jsonb,
  primary key(category,entry_key)
);
insert into public.phase5_codex_catalog(category,entry_key,name_es,name_en,icon,source)
select 'pets',pet_key,name_es,name_en,appearance,origin from public.pet_definitions
on conflict(category,entry_key) do update set name_es=excluded.name_es,name_en=excluded.name_en,icon=excluded.icon,source=excluded.source;
insert into public.phase5_codex_catalog(category,entry_key,name_es,name_en,icon,source) values
 ('resources','ore','Mineral','Ore','⛏️','Recolección'),('resources','wood','Madera','Wood','🌿','Recolección'),('resources','fish','Pez','Fish','🐟','Recolección'),('resources','essence','Esencia','Essence','✨','Combate y Grietas'),
 ('zones','bastion','Bastión','Bastion','🏰','Mundo'),('zones','emberwood','Bosque de Brasas','Emberwood','🌲','Mundo'),('zones','moonwater_coast','Costa Agua Lunar','Moonwater Coast','🌊','Mundo'),('zones','mire','Pantano Susurrante','Whispering Mire','🌫️','Mundo'),('zones','frostpeak','Pico Helado','Frostpeak','❄️','Mundo'),('zones','ashlands','Tierras de Ceniza','Ashlands','🌋','Mundo'),('zones','rift','Grieta','Rift','🌀','Mundo')
on conflict(category,entry_key) do update set name_es=excluded.name_es,name_en=excluded.name_en,icon=excluded.icon,source=excluded.source;

create table if not exists public.character_codex_entries(
  character_id uuid not null references public.characters(id) on delete cascade,
  category text not null,
  entry_key text not null,
  unlocked_at timestamptz not null default now(),
  primary key(character_id,category,entry_key)
);

alter table public.pet_definitions enable row level security;
alter table public.character_pets enable row level security;
alter table public.phase5_action_receipts enable row level security;
alter table public.pet_bonus_bank enable row level security;
alter table public.friend_requests enable row level security;
alter table public.friendships enable row level security;
alter table public.player_presence enable row level security;
alter table public.chat_messages enable row level security;
alter table public.chat_mutes enable row level security;
alter table public.chat_reports enable row level security;
alter table public.phase5_rate_events enable row level security;
alter table public.title_definitions enable row level security;
alter table public.character_titles enable row level security;
alter table public.phase5_weekly_event_definitions enable row level security;
alter table public.phase5_event_templates enable row level security;
alter table public.phase5_event_instances enable row level security;
alter table public.phase5_event_claims enable row level security;
alter table public.player_notifications enable row level security;
alter table public.phase5_rankings enable row level security;
alter table public.phase5_meta enable row level security;
alter table public.phase5_codex_catalog enable row level security;
alter table public.character_codex_entries enable row level security;

revoke all on public.pet_definitions,public.character_pets,public.phase5_action_receipts,public.pet_bonus_bank,public.friend_requests,public.friendships,public.player_presence,public.chat_messages,public.chat_mutes,public.chat_reports,public.phase5_rate_events,public.title_definitions,public.character_titles,public.phase5_weekly_event_definitions,public.phase5_event_templates,public.phase5_event_instances,public.phase5_event_claims,public.player_notifications,public.phase5_rankings,public.phase5_meta,public.phase5_codex_catalog,public.character_codex_entries from anon,authenticated;
grant all on public.pet_definitions,public.character_pets,public.phase5_action_receipts,public.pet_bonus_bank,public.friend_requests,public.friendships,public.player_presence,public.chat_messages,public.chat_mutes,public.chat_reports,public.phase5_rate_events,public.title_definitions,public.character_titles,public.phase5_weekly_event_definitions,public.phase5_event_templates,public.phase5_event_instances,public.phase5_event_claims,public.player_notifications,public.phase5_rankings,public.phase5_meta,public.phase5_codex_catalog,public.character_codex_entries to service_role;
grant usage,select on sequence public.phase5_rate_events_id_seq to service_role;

commit;
