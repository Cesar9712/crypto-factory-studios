-- Nexus Realms Phase 4: Personal Bastion + Clans 2.0
-- Server-authoritative timers, bounded offline production, internal-only clan economy.

create table if not exists public.bastion_building_defs (
  building_key text primary key,
  name_es text not null,
  name_en text not null,
  icon text not null,
  base_gold integer not null check(base_gold>0),
  base_seconds integer not null check(base_seconds>=30),
  primary_resource text not null,
  secondary_resource text not null,
  benefit_es text not null,
  benefit_en text not null,
  produces_resource text,
  production_per_hour numeric(10,2) not null default 0 check(production_per_hour>=0)
);

insert into public.bastion_building_defs(building_key,name_es,name_en,icon,base_gold,base_seconds,primary_resource,secondary_resource,benefit_es,benefit_en,produces_resource,production_per_hour) values
 ('fortress','Fortaleza','Fortress','🏰',180,900,'ore','wood','Desbloqueos globales y mayor límite de progreso offline.','Global unlocks and a larger offline progress limit.',null,0),
 ('blacksmith','Herrería','Blacksmith','⚒️',120,600,'ore','wood','Mejora la eficiencia de fabricación y puede devolver materiales.','Improves crafting efficiency and can refund materials.',null,0),
 ('laboratory','Laboratorio','Laboratory','⚗️',150,720,'fish','wood','Extiende ligeramente los efectos temporales fabricados.','Slightly extends crafted timed effects.',null,0),
 ('garden','Jardín','Garden','🌿',90,420,'wood','fish','Produce ingredientes de forma pasiva con almacenamiento limitado.','Passively produces ingredients with bounded storage.','wood',8),
 ('mine','Mina','Mine','⛏️',110,480,'ore','wood','Produce mineral de forma pasiva con almacenamiento limitado.','Passively produces ore with bounded storage.','ore',7),
 ('pond','Estanque','Pond','🐟',85,390,'fish','wood','Produce pescado de forma pasiva con almacenamiento limitado.','Passively produces fish with bounded storage.','fish',5),
 ('warehouse','Almacén','Warehouse','📦',130,540,'wood','ore','Aumenta la capacidad de almacenamiento del Bastión.','Increases Bastion storage capacity.',null,0),
 ('market','Mercado','Market','🏪',140,600,'wood','ore','Mejora la economía interna y desbloquea utilidades del Bastión.','Improves internal economy and unlocks Bastion utilities.',null,0),
 ('altar','Altar','Altar','✨',160,780,'fish','wood','Activa un buff temporal de regeneración; nunca restaura al instante.','Activates a timed regeneration buff; never restores instantly.',null,0)
on conflict(building_key) do update set
 name_es=excluded.name_es,name_en=excluded.name_en,icon=excluded.icon,base_gold=excluded.base_gold,
 base_seconds=excluded.base_seconds,primary_resource=excluded.primary_resource,secondary_resource=excluded.secondary_resource,
 benefit_es=excluded.benefit_es,benefit_en=excluded.benefit_en,produces_resource=excluded.produces_resource,
 production_per_hour=excluded.production_per_hour;

create table if not exists public.bastion_buildings (
  character_id uuid not null references public.characters(id) on delete cascade,
  building_key text not null references public.bastion_building_defs(building_key) on delete restrict,
  level integer not null default 1 check(level>=1 and level<=50),
  upgrade_to integer,
  upgrade_started_at timestamptz,
  upgrade_finishes_at timestamptz,
  last_production_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key(character_id,building_key),
  check(upgrade_to is null or upgrade_to=level+1)
);

create table if not exists public.bastion_stockpile (
  character_id uuid not null references public.characters(id) on delete cascade,
  resource_key text not null,
  amount bigint not null default 0 check(amount>=0),
  updated_at timestamptz not null default now(),
  primary key(character_id,resource_key)
);

create table if not exists public.bastion_buffs (
  character_id uuid not null references public.characters(id) on delete cascade,
  buff_key text not null,
  starts_at timestamptz not null default now(),
  expires_at timestamptz not null,
  metadata jsonb not null default '{}'::jsonb,
  primary key(character_id,buff_key)
);

create table if not exists public.bastion_activity (
  id uuid primary key default gen_random_uuid(),
  character_id uuid not null references public.characters(id) on delete cascade,
  kind text not null,
  building_key text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists bastion_activity_character_created_idx on public.bastion_activity(character_id,created_at desc);

alter table public.guild_members add column if not exists shop_credits bigint not null default 0 check(shop_credits>=0);

create table if not exists public.guild_treasury_resources (
  guild_id uuid not null references public.guilds(id) on delete cascade,
  resource_key text not null,
  amount bigint not null default 0 check(amount>=0),
  updated_at timestamptz not null default now(),
  primary key(guild_id,resource_key)
);

create table if not exists public.guild_research_definitions (
  research_key text primary key,
  name_es text not null,
  name_en text not null,
  description_es text not null,
  description_en text not null,
  max_level integer not null default 10 check(max_level between 1 and 20),
  effect_per_level numeric(8,4) not null,
  cost_gold_base integer not null check(cost_gold_base>0),
  cost_resource text not null default 'essence',
  cost_resource_base integer not null default 1 check(cost_resource_base>=0)
);
insert into public.guild_research_definitions values
 ('xp_boost','Sabiduría compartida','Shared Wisdom','+1% XP de clan por nivel.','+1% clan XP per level.',10,0.01,250,'essence',2),
 ('gathering','Logística de recolección','Gathering Logistics','Pequeña probabilidad/bonificación de recursos al recolectar.','Small gathering resource bonus.',10,0.02,230,'ore',8),
 ('crafting','Maestría artesanal','Craft Mastery','Pequeña devolución de materiales al fabricar.','Small crafting material refund.',10,0.02,260,'wood',8),
 ('boss_damage','Tácticas de asedio','Siege Tactics','+2% daño al jefe de clan por nivel.','+2% clan boss damage per level.',10,0.02,300,'essence',2)
on conflict(research_key) do update set name_es=excluded.name_es,name_en=excluded.name_en,description_es=excluded.description_es,description_en=excluded.description_en,max_level=excluded.max_level,effect_per_level=excluded.effect_per_level,cost_gold_base=excluded.cost_gold_base,cost_resource=excluded.cost_resource,cost_resource_base=excluded.cost_resource_base;

create table if not exists public.guild_research (
  guild_id uuid not null references public.guilds(id) on delete cascade,
  research_key text not null references public.guild_research_definitions(research_key) on delete restrict,
  level integer not null default 0 check(level>=0),
  updated_at timestamptz not null default now(),
  primary key(guild_id,research_key)
);

create table if not exists public.guild_buffs (
  guild_id uuid not null references public.guilds(id) on delete cascade,
  buff_key text not null,
  starts_at timestamptz not null default now(),
  expires_at timestamptz not null,
  metadata jsonb not null default '{}'::jsonb,
  activated_by uuid references public.characters(id) on delete set null,
  primary key(guild_id,buff_key)
);

create table if not exists public.guild_mission_progress (
  guild_id uuid not null references public.guilds(id) on delete cascade,
  week_start date not null,
  combats bigint not null default 0,
  resources bigint not null default 0,
  crafts bigint not null default 0,
  bosses bigint not null default 0,
  collective_reward_granted_at timestamptz,
  updated_at timestamptz not null default now(),
  primary key(guild_id,week_start)
);

create table if not exists public.guild_mission_claims (
  guild_id uuid not null references public.guilds(id) on delete cascade,
  character_id uuid not null references public.characters(id) on delete cascade,
  week_start date not null,
  claimed_at timestamptz not null default now(),
  primary key(guild_id,character_id,week_start)
);

create table if not exists public.guild_shop_items (
  item_key text primary key,
  name_es text not null,
  name_en text not null,
  description_es text not null,
  description_en text not null,
  cost_credits integer not null check(cost_credits>0),
  reward jsonb not null,
  weekly_limit integer not null default 3 check(weekly_limit between 1 and 20),
  enabled boolean not null default true
);
insert into public.guild_shop_items values
 ('forge_cache','Cofre de Forja','Forge Cache','20 minerales internos de juego.','20 internal game ore.',80,'{"resource":"ore","amount":20}'::jsonb,3,true),
 ('essence_pack','Paquete de Esencia','Essence Pack','4 esencias internas de juego.','4 internal game essence.',110,'{"resource":"essence","amount":4}'::jsonb,2,true),
 ('clan_tonic','Tónico del Clan','Clan Tonic','Buff temporal de regeneración; no restaura al instante.','Timed regeneration buff; no instant restore.',90,'{"regen_minutes":10}'::jsonb,2,true)
on conflict(item_key) do update set name_es=excluded.name_es,name_en=excluded.name_en,description_es=excluded.description_es,description_en=excluded.description_en,cost_credits=excluded.cost_credits,reward=excluded.reward,weekly_limit=excluded.weekly_limit,enabled=excluded.enabled;

create table if not exists public.guild_shop_purchases (
  id uuid primary key default gen_random_uuid(),
  guild_id uuid not null references public.guilds(id) on delete cascade,
  character_id uuid not null references public.characters(id) on delete cascade,
  item_key text not null references public.guild_shop_items(item_key),
  week_start date not null,
  cost_credits integer not null,
  created_at timestamptz not null default now()
);
create index if not exists guild_shop_purchase_week_idx on public.guild_shop_purchases(guild_id,character_id,week_start,item_key);

create table if not exists public.guild_audit_log (
  id uuid primary key default gen_random_uuid(),
  guild_id uuid not null references public.guilds(id) on delete cascade,
  actor_character_id uuid references public.characters(id) on delete set null,
  target_character_id uuid references public.characters(id) on delete set null,
  action text not null,
  amount bigint,
  resource_key text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists guild_audit_guild_created_idx on public.guild_audit_log(guild_id,created_at desc);

create table if not exists public.guild_wars (
  id uuid primary key default gen_random_uuid(),
  week_start date not null,
  guild_a uuid not null references public.guilds(id) on delete cascade,
  guild_b uuid not null references public.guilds(id) on delete cascade,
  score_a bigint not null default 0,
  score_b bigint not null default 0,
  status text not null default 'active' check(status in ('active','finished')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check(guild_a<>guild_b)
);
create unique index if not exists guild_wars_pair_week_unique on public.guild_wars(week_start,least(guild_a,guild_b),greatest(guild_a,guild_b));
create index if not exists guild_wars_week_idx on public.guild_wars(week_start,guild_a,guild_b);

alter table public.bastion_building_defs enable row level security;
alter table public.bastion_buildings enable row level security;
alter table public.bastion_stockpile enable row level security;
alter table public.bastion_buffs enable row level security;
alter table public.bastion_activity enable row level security;
alter table public.guild_treasury_resources enable row level security;
alter table public.guild_research_definitions enable row level security;
alter table public.guild_research enable row level security;
alter table public.guild_buffs enable row level security;
alter table public.guild_mission_progress enable row level security;
alter table public.guild_mission_claims enable row level security;
alter table public.guild_shop_items enable row level security;
alter table public.guild_shop_purchases enable row level security;
alter table public.guild_audit_log enable row level security;
alter table public.guild_wars enable row level security;

revoke all on public.bastion_building_defs,public.bastion_buildings,public.bastion_stockpile,public.bastion_buffs,public.bastion_activity,public.guild_treasury_resources,public.guild_research_definitions,public.guild_research,public.guild_buffs,public.guild_mission_progress,public.guild_mission_claims,public.guild_shop_items,public.guild_shop_purchases,public.guild_audit_log,public.guild_wars from anon,authenticated;
grant select,insert,update,delete on public.bastion_building_defs,public.bastion_buildings,public.bastion_stockpile,public.bastion_buffs,public.bastion_activity,public.guild_treasury_resources,public.guild_research_definitions,public.guild_research,public.guild_buffs,public.guild_mission_progress,public.guild_mission_claims,public.guild_shop_items,public.guild_shop_purchases,public.guild_audit_log,public.guild_wars to service_role;

create or replace function public.phase4_storage_cap(p_character uuid)
returns integer language sql stable security definer set search_path=public as $$
  select 180 + coalesce((select level from public.bastion_buildings where character_id=p_character and building_key='warehouse'),1)*120
             + coalesce((select level from public.bastion_buildings where character_id=p_character and building_key='fortress'),1)*20
$$;

create or replace function public.phase4_offline_cap_hours(p_character uuid)
returns integer language sql stable security definer set search_path=public as $$
  select least(12,4 + coalesce((select level from public.bastion_buildings where character_id=p_character and building_key='warehouse'),1)*2
                  + floor(coalesce((select level from public.bastion_buildings where character_id=p_character and building_key='fortress'),1)/2.0)::integer)
$$;

create or replace function public.phase4_ensure_bastion(p_character uuid)
returns void language plpgsql security definer set search_path=public as $$
begin
  if not exists(select 1 from public.characters where id=p_character) then raise exception 'Character not found'; end if;
  insert into public.bastion_buildings(character_id,building_key)
  select p_character,d.building_key from public.bastion_building_defs d
  on conflict(character_id,building_key) do nothing;
  insert into public.bastion_stockpile(character_id,resource_key,amount)
  values(p_character,'ore',0),(p_character,'wood',0),(p_character,'fish',0),(p_character,'essence',0)
  on conflict(character_id,resource_key) do nothing;
end;$$;

create or replace function public.phase4_settle_bastion(p_character uuid)
returns void language plpgsql security definer set search_path=public as $$
declare
  r record; v_now timestamptz:=now(); v_raw bigint; v_used bigint; v_ticks bigint; v_gain bigint;
  v_cap integer; v_offline integer; v_stock bigint; v_room bigint;
begin
  perform public.phase4_ensure_bastion(p_character);
  update public.bastion_buildings
    set level=upgrade_to,upgrade_to=null,upgrade_started_at=null,upgrade_finishes_at=null,updated_at=v_now
    where character_id=p_character and upgrade_to is not null and upgrade_finishes_at<=v_now;
  v_cap:=public.phase4_storage_cap(p_character);
  v_offline:=public.phase4_offline_cap_hours(p_character);
  select coalesce(sum(amount),0) into v_stock from public.bastion_stockpile where character_id=p_character;
  for r in
    select b.building_key,b.level,b.last_production_at,d.produces_resource,d.production_per_hour
    from public.bastion_buildings b join public.bastion_building_defs d using(building_key)
    where b.character_id=p_character and d.produces_resource is not null and d.production_per_hour>0
    for update of b
  loop
    v_raw:=greatest(0,floor(extract(epoch from (v_now-r.last_production_at)))::bigint);
    v_used:=least(v_raw,(v_offline*3600)::bigint);
    v_ticks:=floor(v_used/600.0)::bigint;
    if v_ticks>0 then
      v_gain:=floor(v_ticks*number(r.production_per_hour)*r.level/6.0)::bigint;
      v_room:=greatest(0,v_cap-v_stock);
      v_gain:=least(v_gain,v_room);
      if v_gain>0 then
        insert into public.bastion_stockpile(character_id,resource_key,amount,updated_at)
        values(p_character,r.produces_resource,v_gain,v_now)
        on conflict(character_id,resource_key) do update set amount=public.bastion_stockpile.amount+excluded.amount,updated_at=v_now;
        v_stock:=v_stock+v_gain;
      end if;
      update public.bastion_buildings set last_production_at=case when v_raw>v_offline*3600 then v_now else last_production_at+(v_ticks*600)*interval '1 second' end,updated_at=v_now
      where character_id=p_character and building_key=r.building_key;
    elsif v_raw>v_offline*3600 then
      update public.bastion_buildings set last_production_at=v_now,updated_at=v_now where character_id=p_character and building_key=r.building_key;
    end if;
  end loop;
  delete from public.bastion_buffs where character_id=p_character and expires_at<=v_now;
end;$$;

create or replace function public.phase4_bastion_upgrade(p_character uuid,p_building text)
returns table(building_key text,upgrade_to integer,finishes_at timestamptz,gold_cost bigint,primary_cost integer,secondary_cost integer,essence_cost integer)
language plpgsql security definer set search_path=public as $$
declare
  b public.bastion_buildings%rowtype; d public.bastion_building_defs%rowtype;
  v_next integer; v_gold bigint; v_primary integer; v_secondary integer; v_essence integer:=0; v_seconds integer;
  v_fortress integer; v_have bigint;
begin
  perform public.phase4_settle_bastion(p_character);
  select * into b from public.bastion_buildings where character_id=p_character and building_key=p_building for update;
  select * into d from public.bastion_building_defs where building_key=p_building;
  if b.character_id is null or d.building_key is null then raise exception 'Unknown Bastion building'; end if;
  if b.upgrade_to is not null then raise exception 'Building upgrade already active'; end if;
  v_next:=b.level+1;
  select level into v_fortress from public.bastion_buildings where character_id=p_character and building_key='fortress';
  if p_building<>'fortress' and v_next>v_fortress+2 then raise exception 'Fortaleza level too low for this upgrade'; end if;
  v_gold:=ceil(d.base_gold*power(v_next::numeric,1.55))::bigint;
  v_primary:=ceil((8+d.base_gold/70.0)*v_next)::integer;
  v_secondary:=ceil(4*v_next)::integer;
  if p_building in ('fortress','laboratory','altar') and v_next>=4 then v_essence:=ceil(v_next/2.0)::integer; end if;
  v_seconds:=ceil(d.base_seconds*power(v_next::numeric,1.30))::integer;
  update public.characters set gold=gold-v_gold where id=p_character and gold>=v_gold;
  if not found then raise exception 'Not enough gold'; end if;
  select amount into v_have from public.resources where character_id=p_character and resource_key=d.primary_resource for update;
  if coalesce(v_have,0)<v_primary then raise exception 'Not enough %',d.primary_resource; end if;
  update public.resources set amount=amount-v_primary where character_id=p_character and resource_key=d.primary_resource;
  select amount into v_have from public.resources where character_id=p_character and resource_key=d.secondary_resource for update;
  if coalesce(v_have,0)<v_secondary then raise exception 'Not enough %',d.secondary_resource; end if;
  update public.resources set amount=amount-v_secondary where character_id=p_character and resource_key=d.secondary_resource;
  if v_essence>0 then
    select amount into v_have from public.resources where character_id=p_character and resource_key='essence' for update;
    if coalesce(v_have,0)<v_essence then raise exception 'Not enough essence'; end if;
    update public.resources set amount=amount-v_essence where character_id=p_character and resource_key='essence';
  end if;
  update public.bastion_buildings set upgrade_to=v_next,upgrade_started_at=now(),upgrade_finishes_at=now()+v_seconds*interval '1 second',updated_at=now()
  where character_id=p_character and building_key=p_building;
  insert into public.bastion_activity(character_id,kind,building_key,metadata) values(p_character,'upgrade_started',p_building,jsonb_build_object('to',v_next,'gold',v_gold,'seconds',v_seconds));
  return query select p_building,v_next,now()+v_seconds*interval '1 second',v_gold,v_primary,v_secondary,v_essence;
exception when others then
  raise;
end;$$;

create or replace function public.phase4_bastion_claim(p_character uuid)
returns jsonb language plpgsql security definer set search_path=public as $$
declare r record; v_claim jsonb:='{}'::jsonb;
begin
  perform public.phase4_settle_bastion(p_character);
  for r in select resource_key,amount from public.bastion_stockpile where character_id=p_character and amount>0 for update loop
    insert into public.resources(character_id,resource_key,amount) values(p_character,r.resource_key,r.amount)
    on conflict(character_id,resource_key) do update set amount=public.resources.amount+excluded.amount;
    v_claim:=v_claim||jsonb_build_object(r.resource_key,r.amount);
    update public.bastion_stockpile set amount=0,updated_at=now() where character_id=p_character and resource_key=r.resource_key;
  end loop;
  insert into public.bastion_activity(character_id,kind,metadata) values(p_character,'stockpile_claimed',v_claim);
  return v_claim;
end;$$;

create or replace function public.phase4_activate_altar(p_character uuid)
returns timestamptz language plpgsql security definer set search_path=public as $$
declare v_level integer; v_gold bigint; v_ess integer; v_minutes integer; v_until timestamptz; v_have bigint;
begin
  perform public.phase4_settle_bastion(p_character);
  select level into v_level from public.bastion_buildings where character_id=p_character and building_key='altar' for update;
  if coalesce(v_level,1)<2 then raise exception 'Altar level 2 required'; end if;
  v_gold:=40*v_level; v_ess:=greatest(1,ceil(v_level/2.0)::integer); v_minutes:=least(60,10+v_level*5);
  update public.characters set gold=gold-v_gold where id=p_character and gold>=v_gold;
  if not found then raise exception 'Not enough gold'; end if;
  select amount into v_have from public.resources where character_id=p_character and resource_key='essence' for update;
  if coalesce(v_have,0)<v_ess then raise exception 'Not enough essence'; end if;
  update public.resources set amount=amount-v_ess where character_id=p_character and resource_key='essence';
  update public.characters set regen_boost_until=greatest(coalesce(regen_boost_until,now()),now())+v_minutes*interval '1 minute' where id=p_character returning regen_boost_until into v_until;
  insert into public.bastion_buffs(character_id,buff_key,starts_at,expires_at,metadata) values(p_character,'altar_regen',now(),v_until,jsonb_build_object('level',v_level,'minutes',v_minutes)) on conflict(character_id,buff_key) do update set starts_at=excluded.starts_at,expires_at=excluded.expires_at,metadata=excluded.metadata;
  insert into public.bastion_activity(character_id,kind,building_key,metadata) values(p_character,'buff_activated','altar',jsonb_build_object('expires_at',v_until,'gold',v_gold,'essence',v_ess));
  return v_until;
end;$$;

create or replace function public.phase4_ensure_clan_week(p_guild uuid)
returns void language plpgsql security definer set search_path=public as $$
declare v_week date:=public.current_game_week();
begin
  if p_guild is null then return; end if;
  insert into public.guild_mission_progress(guild_id,week_start) values(p_guild,v_week) on conflict do nothing;
  insert into public.guild_research(guild_id,research_key,level) select p_guild,research_key,0 from public.guild_research_definitions on conflict do nothing;
  insert into public.guild_treasury_resources(guild_id,resource_key,amount) values(p_guild,'ore',0),(p_guild,'wood',0),(p_guild,'fish',0),(p_guild,'essence',0) on conflict do nothing;
  delete from public.guild_buffs where guild_id=p_guild and expires_at<=now();
end;$$;

create or replace function public.phase4_clan_role(p_character uuid,p_guild uuid)
returns text language sql stable security definer set search_path=public as $$
 select role from public.guild_members where character_id=p_character and guild_id=p_guild
$$;

create or replace function public.phase4_clan_donate(p_character uuid,p_gold integer default 0,p_resource text default null,p_amount integer default 0)
returns void language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_gold integer:=greatest(0,coalesce(p_gold,0)); v_amount integer:=greatest(0,coalesce(p_amount,0)); v_have bigint;
begin
  select guild_id into v_guild from public.guild_members where character_id=p_character;
  if v_guild is null then raise exception 'Not in a clan'; end if;
  if v_gold=0 and v_amount=0 then raise exception 'Donation must be positive'; end if;
  if v_gold>1000000 or v_amount>1000000 then raise exception 'Donation exceeds limit'; end if;
  if v_gold>0 then
    update public.characters set gold=gold-v_gold where id=p_character and gold>=v_gold;
    if not found then raise exception 'Not enough gold'; end if;
    update public.guilds set treasury_demo=treasury_demo+v_gold,updated_at=now() where id=v_guild;
    insert into public.guild_audit_log(guild_id,actor_character_id,action,amount,resource_key) values(v_guild,p_character,'donation',v_gold,'gold');
  end if;
  if v_amount>0 then
    if p_resource not in ('ore','wood','fish','essence') then raise exception 'Invalid resource'; end if;
    select amount into v_have from public.resources where character_id=p_character and resource_key=p_resource for update;
    if coalesce(v_have,0)<v_amount then raise exception 'Not enough resource'; end if;
    update public.resources set amount=amount-v_amount where character_id=p_character and resource_key=p_resource;
    insert into public.guild_treasury_resources(guild_id,resource_key,amount,updated_at) values(v_guild,p_resource,v_amount,now()) on conflict(guild_id,resource_key) do update set amount=public.guild_treasury_resources.amount+excluded.amount,updated_at=now();
    insert into public.guild_audit_log(guild_id,actor_character_id,action,amount,resource_key) values(v_guild,p_character,'donation',v_amount,p_resource);
  end if;
end;$$;

create or replace function public.phase4_clan_research(p_character uuid,p_research text)
returns integer language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_role text; d public.guild_research_definitions%rowtype; v_level integer; v_next integer; v_gold bigint; v_res integer; v_have bigint;
begin
  select guild_id,role into v_guild,v_role from public.guild_members where character_id=p_character;
  if v_guild is null then raise exception 'Not in a clan'; end if;
  if v_role not in ('leader','officer') then raise exception 'Officer permission required'; end if;
  perform public.phase4_ensure_clan_week(v_guild);
  select * into d from public.guild_research_definitions where research_key=p_research;
  if d.research_key is null then raise exception 'Unknown research'; end if;
  select level into v_level from public.guild_research where guild_id=v_guild and research_key=p_research for update;
  if v_level>=d.max_level then raise exception 'Research maxed'; end if;
  v_next:=v_level+1; v_gold:=ceil(d.cost_gold_base*power(v_next::numeric,1.45))::bigint; v_res:=d.cost_resource_base*v_next;
  update public.guilds set treasury_demo=treasury_demo-v_gold,updated_at=now() where id=v_guild and treasury_demo>=v_gold;
  if not found then raise exception 'Clan treasury gold too low'; end if;
  select amount into v_have from public.guild_treasury_resources where guild_id=v_guild and resource_key=d.cost_resource for update;
  if coalesce(v_have,0)<v_res then raise exception 'Clan treasury resource too low'; end if;
  update public.guild_treasury_resources set amount=amount-v_res,updated_at=now() where guild_id=v_guild and resource_key=d.cost_resource;
  update public.guild_research set level=v_next,updated_at=now() where guild_id=v_guild and research_key=p_research;
  insert into public.guild_audit_log(guild_id,actor_character_id,action,amount,resource_key,metadata) values(v_guild,p_character,'research_spend',v_gold,'gold',jsonb_build_object('research',p_research,'level',v_next,'resource',d.cost_resource,'resource_amount',v_res));
  return v_next;
end;$$;

create or replace function public.phase4_clan_activate_buff(p_character uuid,p_buff text)
returns timestamptz language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_role text; v_gold integer; v_ess integer; v_minutes integer; v_until timestamptz; v_have bigint;
begin
  select guild_id,role into v_guild,v_role from public.guild_members where character_id=p_character;
  if v_guild is null then raise exception 'Not in a clan'; end if;
  if v_role not in ('leader','officer') then raise exception 'Officer permission required'; end if;
  if p_buff='gathering_rally' then v_gold:=350;v_ess:=4;v_minutes:=60;
  elsif p_buff='boss_fury' then v_gold:=450;v_ess:=5;v_minutes:=60;
  else raise exception 'Unknown clan buff'; end if;
  update public.guilds set treasury_demo=treasury_demo-v_gold,updated_at=now() where id=v_guild and treasury_demo>=v_gold;
  if not found then raise exception 'Clan treasury gold too low'; end if;
  select amount into v_have from public.guild_treasury_resources where guild_id=v_guild and resource_key='essence' for update;
  if coalesce(v_have,0)<v_ess then raise exception 'Clan treasury essence too low'; end if;
  update public.guild_treasury_resources set amount=amount-v_ess,updated_at=now() where guild_id=v_guild and resource_key='essence';
  v_until:=now()+v_minutes*interval '1 minute';
  insert into public.guild_buffs(guild_id,buff_key,starts_at,expires_at,metadata,activated_by) values(v_guild,p_buff,now(),v_until,jsonb_build_object('minutes',v_minutes),p_character) on conflict(guild_id,buff_key) do update set starts_at=excluded.starts_at,expires_at=excluded.expires_at,metadata=excluded.metadata,activated_by=excluded.activated_by;
  insert into public.guild_audit_log(guild_id,actor_character_id,action,amount,resource_key,metadata) values(v_guild,p_character,'buff_spend',v_gold,'gold',jsonb_build_object('buff',p_buff,'essence',v_ess,'expires_at',v_until));
  return v_until;
end;$$;

create or replace function public.phase4_clan_claim_mission(p_character uuid)
returns void language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_week date:=public.current_game_week(); v_members integer; p public.guild_mission_progress%rowtype; t_combat bigint; t_res bigint; t_craft bigint; t_boss bigint;
begin
  select guild_id into v_guild from public.guild_members where character_id=p_character;
  if v_guild is null then raise exception 'Not in a clan'; end if;
  perform public.phase4_ensure_clan_week(v_guild);
  select count(*) into v_members from public.guild_members where guild_id=v_guild;
  t_combat:=50+12*v_members; t_res:=800+210*v_members; t_craft:=20+9*v_members; t_boss:=10+ceil(4.5*v_members)::integer;
  select * into p from public.guild_mission_progress where guild_id=v_guild and week_start=v_week for update;
  if p.combats<t_combat or p.resources<t_res or p.crafts<t_craft or p.bosses<t_boss then raise exception 'Clan mission incomplete'; end if;
  if exists(select 1 from public.guild_mission_claims where guild_id=v_guild and character_id=p_character and week_start=v_week) then raise exception 'Clan mission already claimed'; end if;
  if p.collective_reward_granted_at is null then
    update public.guild_mission_progress set collective_reward_granted_at=now(),updated_at=now() where guild_id=v_guild and week_start=v_week;
    update public.guilds set treasury_demo=treasury_demo+300,xp=xp+250,level=least(20,1+floor(sqrt((xp+250)::numeric/250.0))::integer),updated_at=now() where id=v_guild;
    insert into public.guild_audit_log(guild_id,actor_character_id,action,amount,resource_key) values(v_guild,p_character,'mission_collective_reward',300,'gold');
  end if;
  insert into public.guild_mission_claims(guild_id,character_id,week_start) values(v_guild,p_character,v_week);
  update public.characters set gold=gold+120,renown=coalesce(renown,0)+2 where id=p_character;
  insert into public.resources(character_id,resource_key,amount) values(p_character,'essence',2) on conflict(character_id,resource_key) do update set amount=public.resources.amount+2;
  update public.guild_members set shop_credits=shop_credits+40 where guild_id=v_guild and character_id=p_character;
end;$$;

create or replace function public.phase4_clan_shop_buy(p_character uuid,p_item text)
returns void language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_week date:=public.current_game_week(); i public.guild_shop_items%rowtype; v_count integer; v_credits bigint; v_resource text; v_amount integer; v_minutes integer;
begin
  select guild_id,shop_credits into v_guild,v_credits from public.guild_members where character_id=p_character for update;
  if v_guild is null then raise exception 'Not in a clan'; end if;
  select * into i from public.guild_shop_items where item_key=p_item and enabled;
  if i.item_key is null then raise exception 'Shop item unavailable'; end if;
  select count(*) into v_count from public.guild_shop_purchases where guild_id=v_guild and character_id=p_character and week_start=v_week and item_key=p_item;
  if v_count>=i.weekly_limit then raise exception 'Weekly shop limit reached'; end if;
  if v_credits<i.cost_credits then raise exception 'Not enough clan shop credits'; end if;
  update public.guild_members set shop_credits=shop_credits-i.cost_credits where guild_id=v_guild and character_id=p_character;
  v_resource:=i.reward->>'resource'; v_amount:=coalesce((i.reward->>'amount')::integer,0); v_minutes:=coalesce((i.reward->>'regen_minutes')::integer,0);
  if v_resource is not null and v_amount>0 then insert into public.resources(character_id,resource_key,amount) values(p_character,v_resource,v_amount) on conflict(character_id,resource_key) do update set amount=public.resources.amount+v_amount; end if;
  if v_minutes>0 then update public.characters set regen_boost_until=greatest(coalesce(regen_boost_until,now()),now())+least(30,v_minutes)*interval '1 minute' where id=p_character; end if;
  insert into public.guild_shop_purchases(guild_id,character_id,item_key,week_start,cost_credits) values(v_guild,p_character,p_item,v_week,i.cost_credits);
  insert into public.guild_audit_log(guild_id,actor_character_id,action,amount,resource_key,metadata) values(v_guild,p_character,'shop_purchase',i.cost_credits,'shop_credits',jsonb_build_object('item',p_item));
end;$$;

create or replace function public.phase4_war_score(p_guild uuid)
returns bigint language sql stable security definer set search_path=public as $$
  select coalesce((select sum(weekly_points) from public.guild_members where guild_id=p_guild),0)::bigint
       + floor(coalesce((select sum(damage) from public.guild_raid_contributions where guild_id=p_guild and week_start=public.current_game_week()),0)/100.0)::bigint
$$;

create or replace function public.phase4_ensure_war(p_guild uuid)
returns uuid language plpgsql security definer set search_path=public as $$
declare v_week date:=public.current_game_week(); v_id uuid; v_other uuid;
begin
  if p_guild is null then return null; end if;
  select id into v_id from public.guild_wars where week_start=v_week and (guild_a=p_guild or guild_b=p_guild) limit 1;
  if v_id is null then
    select g.id into v_other from public.guilds g where g.id<>p_guild and not exists(select 1 from public.guild_wars w where w.week_start=v_week and (w.guild_a=g.id or w.guild_b=g.id)) order by g.level desc,g.xp desc,g.id limit 1;
    if v_other is not null then
      insert into public.guild_wars(week_start,guild_a,guild_b) values(v_week,p_guild,v_other) returning id into v_id;
    end if;
  end if;
  if v_id is not null then
    update public.guild_wars set score_a=public.phase4_war_score(guild_a),score_b=public.phase4_war_score(guild_b),status=case when now()>=((v_week+7)::date)::timestamptz then 'finished' else 'active' end,updated_at=now() where id=v_id;
  end if;
  return v_id;
end;$$;

-- Extend existing guild progress instead of replacing the clan system.
create or replace function public.add_guild_progress(p_character_id uuid,p_kind text,p_amount integer default 1,p_xp integer default 1)
returns void language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_week date:=public.current_game_week(); v_add integer:=greatest(0,coalesce(p_amount,0)); v_xp integer:=greatest(0,coalesce(p_xp,0)); v_xp_level integer:=0; v_effective_xp integer;
begin
  select guild_id into v_guild from public.guild_members where character_id=p_character_id limit 1;
  if v_guild is null then return; end if;
  perform public.ensure_guild_week(v_guild); perform public.phase4_ensure_clan_week(v_guild);
  if p_kind='combat' then update public.guild_weekly_progress set combat=combat+v_add,updated_at=now() where guild_id=v_guild and week_start=v_week;
  elsif p_kind='gather' then update public.guild_weekly_progress set gather=gather+v_add,updated_at=now() where guild_id=v_guild and week_start=v_week;
  elsif p_kind='craft' then update public.guild_weekly_progress set craft=craft+v_add,updated_at=now() where guild_id=v_guild and week_start=v_week;
  elsif p_kind='expedition' then update public.guild_weekly_progress set expedition=expedition+v_add,updated_at=now() where guild_id=v_guild and week_start=v_week;
  elsif p_kind='boss' then update public.guild_weekly_progress set boss=boss+v_add,updated_at=now() where guild_id=v_guild and week_start=v_week; end if;
  if p_kind='combat' then update public.guild_mission_progress set combats=combats+v_add,updated_at=now() where guild_id=v_guild and week_start=v_week;
  elsif p_kind='craft' then update public.guild_mission_progress set crafts=crafts+v_add,updated_at=now() where guild_id=v_guild and week_start=v_week;
  elsif p_kind='boss' then update public.guild_mission_progress set bosses=bosses+v_add,updated_at=now() where guild_id=v_guild and week_start=v_week; end if;
  select level into v_xp_level from public.guild_research where guild_id=v_guild and research_key='xp_boost';
  v_effective_xp:=greatest(0,floor(v_xp*(1+coalesce(v_xp_level,0)*0.01))::integer);
  update public.guild_members set contribution_points=contribution_points+v_xp,weekly_points=weekly_points+v_xp,shop_credits=shop_credits+v_xp where guild_id=v_guild and character_id=p_character_id;
  update public.guilds set xp=xp+v_effective_xp,level=least(20,1+floor(sqrt((xp+v_effective_xp)::numeric/250.0))::integer),updated_at=now() where id=v_guild;
end;$$;

create or replace function public.guild_progress_from_transaction()
returns trigger language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_week date:=public.current_game_week(); v_total integer:=0; v_level integer:=0; v_key text; v_bonus integer:=0;
begin
  if new.kind='gather' then
    perform public.add_guild_progress(new.character_id,'gather',1,2);
    v_total:=greatest(0,coalesce((new.delta->>'ore')::integer,0))+greatest(0,coalesce((new.delta->>'wood')::integer,0))+greatest(0,coalesce((new.delta->>'fish')::integer,0));
    select guild_id into v_guild from public.guild_members where character_id=new.character_id;
    if v_guild is not null then
      perform public.phase4_ensure_clan_week(v_guild);
      update public.guild_mission_progress set resources=resources+v_total,updated_at=now() where guild_id=v_guild and week_start=v_week;
      select level into v_level from public.guild_research where guild_id=v_guild and research_key='gathering';
      if exists(select 1 from public.guild_buffs where guild_id=v_guild and buff_key='gathering_rally' and expires_at>now()) then v_level:=coalesce(v_level,0)+2; end if;
      if coalesce(v_level,0)>0 then
        v_key:=case when coalesce((new.delta->>'ore')::integer,0)>0 then 'ore' when coalesce((new.delta->>'wood')::integer,0)>0 then 'wood' when coalesce((new.delta->>'fish')::integer,0)>0 then 'fish' else null end;
        v_bonus:=floor(v_total*least(0.20,coalesce(v_level,0)*0.02))::integer;
        if v_key is not null and v_bonus>0 then insert into public.resources(character_id,resource_key,amount) values(new.character_id,v_key,v_bonus) on conflict(character_id,resource_key) do update set amount=public.resources.amount+v_bonus; end if;
      end if;
    end if;
  elsif new.kind='combat_reward' then
    perform public.add_guild_progress(new.character_id,'combat',1,3);
    if coalesce((new.delta->>'boss')::boolean,false) then perform public.add_guild_progress(new.character_id,'boss',1,8); end if;
  end if;
  return new;
end;$$;

create or replace function public.guild_progress_from_craft()
returns trigger language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_level integer:=0; v_cost jsonb; v_key text; v_amount integer; v_refund integer;
begin
  perform public.add_guild_progress(new.character_id,'craft',1,4);
  select guild_id into v_guild from public.guild_members where character_id=new.character_id;
  if v_guild is not null then
    select level into v_level from public.guild_research where guild_id=v_guild and research_key='crafting';
    if coalesce(v_level,0)>0 then
      select cost into v_cost from public.crafting_recipes where id=new.recipe_id;
      v_key:=case when coalesce((v_cost->>'ore')::integer,0)>0 then 'ore' when coalesce((v_cost->>'wood')::integer,0)>0 then 'wood' when coalesce((v_cost->>'fish')::integer,0)>0 then 'fish' when coalesce((v_cost->>'essence')::integer,0)>0 then 'essence' else null end;
      if v_key is not null then
        v_amount:=coalesce((v_cost->>v_key)::integer,0); v_refund:=floor(v_amount*least(0.20,v_level*0.02))::integer;
        if v_refund>0 then insert into public.resources(character_id,resource_key,amount) values(new.character_id,v_key,v_refund) on conflict(character_id,resource_key) do update set amount=public.resources.amount+v_refund; end if;
      end if;
    end if;
  end if;
  return new;
end;$$;

create or replace function public.phase4_bastion_craft_benefit()
returns trigger language plpgsql security definer set search_path=public as $$
declare v_smith integer:=1; v_lab integer:=1; v_cost jsonb; v_key text; v_refund integer; v_minutes integer;
begin
  perform public.phase4_ensure_bastion(new.character_id);
  select level into v_smith from public.bastion_buildings where character_id=new.character_id and building_key='blacksmith';
  select level into v_lab from public.bastion_buildings where character_id=new.character_id and building_key='laboratory';
  if coalesce(v_smith,1)>1 then
    select cost into v_cost from public.crafting_recipes where id=new.recipe_id;
    v_key:=case when coalesce((v_cost->>'ore')::integer,0)>0 then 'ore' when coalesce((v_cost->>'wood')::integer,0)>0 then 'wood' when coalesce((v_cost->>'fish')::integer,0)>0 then 'fish' else null end;
    v_refund:=least(2,greatest(0,floor((v_smith-1)/2.0)::integer+1));
    if v_key is not null and v_refund>0 then insert into public.resources(character_id,resource_key,amount) values(new.character_id,v_key,v_refund) on conflict(character_id,resource_key) do update set amount=public.resources.amount+v_refund; end if;
  end if;
  if coalesce(v_lab,1)>1 and coalesce((new.result->>'consumable')::boolean,false) then
    v_minutes:=least(10,v_lab-1);
    update public.characters set regen_boost_until=greatest(coalesce(regen_boost_until,now()),now())+v_minutes*interval '1 minute' where id=new.character_id;
  end if;
  return new;
end;$$;
drop trigger if exists trg_phase4_bastion_craft on public.crafting_log;
create trigger trg_phase4_bastion_craft after insert on public.crafting_log for each row execute function public.phase4_bastion_craft_benefit();

-- Replace raid calculation only to add small Clan 2.0 research/buff modifiers while preserving the existing boss system.
create or replace function public.clan_raid_attack(p_character_id uuid)
returns table(applied_damage bigint,remaining_hp bigint,defeated boolean)
language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_week date:=public.current_game_week(); v_energy integer; v_max_energy integer; v_last timestamptz; v_loc text; v_minutes integer; v_rate integer; v_level integer; v_atk integer; v_crit numeric; v_eqatk integer; v_damage bigint; v_hp bigint; v_research integer:=0; v_mult numeric:=1;
begin
  select guild_id into v_guild from public.guild_members where character_id=p_character_id;
  if v_guild is null then raise exception 'Not in a clan'; end if;
  perform public.ensure_guild_week(v_guild); perform public.phase4_ensure_clan_week(v_guild);
  select energy,max_energy,last_tick,location,level into v_energy,v_max_energy,v_last,v_loc,v_level from public.characters where id=p_character_id for update;
  if v_energy is null then raise exception 'Character not found'; end if;
  v_minutes:=greatest(0,floor(extract(epoch from (now()-coalesce(v_last,now())))/60)::integer); v_rate:=case when v_loc='bastion' then 2 else 1 end;
  if v_minutes>0 then v_energy:=least(v_max_energy,v_energy+v_minutes*v_rate); update public.characters set energy=v_energy,last_tick=coalesce(v_last,now())+(v_minutes||' minutes')::interval where id=p_character_id; end if;
  if v_energy<18 then raise exception 'Not enough energy: need 18'; end if;
  select atk,crit into v_atk,v_crit from public.character_stats where character_id=p_character_id;
  select coalesce(sum(ii.atk),0)::integer into v_eqatk from public.equipment e left join public.item_instances ii on ii.id in (e.weapon_item_id,e.helmet_item_id,e.armor_item_id,e.gloves_item_id,e.boots_item_id,e.ring_item_id) where e.character_id=p_character_id;
  select current_hp into v_hp from public.guild_raids where guild_id=v_guild and week_start=v_week and status='active' for update;
  if v_hp is null or v_hp<=0 then raise exception 'Clan raid is not active'; end if;
  select level into v_research from public.guild_research where guild_id=v_guild and research_key='boss_damage';
  v_mult:=1+coalesce(v_research,0)*0.02; if exists(select 1 from public.guild_buffs where guild_id=v_guild and buff_key='boss_fury' and expires_at>now()) then v_mult:=v_mult+0.05; end if;
  v_damage:=greatest(30,floor(((coalesce(v_atk,10)+coalesce(v_eqatk,0)+v_level*2)*2+floor(random()*35))*v_mult)::bigint); if random()<coalesce(v_crit,0) then v_damage:=floor(v_damage*1.5); end if; v_damage:=least(v_damage,v_hp);
  update public.characters set energy=v_energy-18 where id=p_character_id;
  update public.guild_raids set current_hp=greatest(0,current_hp-v_damage),status=case when current_hp-v_damage<=0 then 'defeated' else status end,updated_at=now() where guild_id=v_guild and week_start=v_week returning current_hp into v_hp;
  insert into public.guild_raid_contributions(guild_id,week_start,character_id,damage,attempts,updated_at) values(v_guild,v_week,p_character_id,v_damage,1,now()) on conflict(guild_id,week_start,character_id) do update set damage=public.guild_raid_contributions.damage+excluded.damage,attempts=public.guild_raid_contributions.attempts+1,updated_at=now();
  update public.guild_members set contribution_points=contribution_points+5,weekly_points=weekly_points+5,shop_credits=shop_credits+5 where guild_id=v_guild and character_id=p_character_id;
  if v_hp<=0 then update public.guilds set xp=xp+100,level=least(20,1+floor(sqrt((xp+100)::numeric/250.0))::integer),updated_at=now() where id=v_guild; end if;
  perform public.phase4_ensure_war(v_guild);
  return query select v_damage,v_hp,v_hp<=0;
end;$$;

-- Role permissions and anti-abuse audit: extend the existing clan helpers, do not rebuild create/join/leave.
create or replace function public.clan_set_role(p_character_id uuid,p_target_character_id uuid,p_role text)
returns void language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_role text; v_old text;
begin
 select guild_id,role into v_guild,v_role from public.guild_members where character_id=p_character_id;
 if v_guild is null or v_role<>'leader' then raise exception 'Leader permission required'; end if;
 if p_target_character_id=p_character_id then raise exception 'Cannot change your own leader role'; end if;
 if p_role not in ('member','officer') then raise exception 'Invalid clan role'; end if;
 select role into v_old from public.guild_members where guild_id=v_guild and character_id=p_target_character_id for update;
 if v_old is null then raise exception 'Member not found'; end if;
 if v_old='leader' then raise exception 'Cannot change leader role'; end if;
 update public.guild_members set role=p_role where guild_id=v_guild and character_id=p_target_character_id;
 insert into public.guild_activity(guild_id,character_id,kind,metadata) values(v_guild,p_character_id,'role_changed',jsonb_build_object('target',p_target_character_id,'from',v_old,'role',p_role));
 insert into public.guild_audit_log(guild_id,actor_character_id,target_character_id,action,metadata) values(v_guild,p_character_id,p_target_character_id,'role_change',jsonb_build_object('from',v_old,'to',p_role));
end;$$;

create or replace function public.clan_kick(p_character_id uuid,p_target_character_id uuid)
returns void language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_role text; v_target_role text;
begin
 select guild_id,role into v_guild,v_role from public.guild_members where character_id=p_character_id;
 if v_guild is null or v_role not in ('leader','officer') then raise exception 'Officer permission required'; end if;
 if p_target_character_id=p_character_id then raise exception 'Cannot kick self'; end if;
 select role into v_target_role from public.guild_members where guild_id=v_guild and character_id=p_target_character_id for update;
 if v_target_role is null then raise exception 'Member not found'; end if;
 if v_target_role='leader' or (v_role='officer' and v_target_role<>'member') then raise exception 'Insufficient role permission'; end if;
 insert into public.guild_activity(guild_id,character_id,kind,metadata) values(v_guild,p_character_id,'kicked',jsonb_build_object('target',p_target_character_id,'target_role',v_target_role));
 insert into public.guild_audit_log(guild_id,actor_character_id,target_character_id,action,metadata) values(v_guild,p_character_id,p_target_character_id,'kick',jsonb_build_object('target_role',v_target_role));
 delete from public.guild_members where guild_id=v_guild and character_id=p_target_character_id;
end;$$;

create or replace function public.clan_transfer_leadership(p_character_id uuid,p_target_character_id uuid)
returns void language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_role text; v_target_role text;
begin
 select guild_id,role into v_guild,v_role from public.guild_members where character_id=p_character_id for update;
 if v_guild is null or v_role<>'leader' then raise exception 'Leader permission required'; end if;
 if p_target_character_id=p_character_id then raise exception 'Already clan leader'; end if;
 select role into v_target_role from public.guild_members where guild_id=v_guild and character_id=p_target_character_id for update;
 if v_target_role is null then raise exception 'Member not found'; end if;
 update public.guild_members set role='officer' where guild_id=v_guild and character_id=p_character_id;
 update public.guild_members set role='leader' where guild_id=v_guild and character_id=p_target_character_id;
 update public.guilds set owner_character_id=p_target_character_id,updated_at=now() where id=v_guild;
 insert into public.guild_activity(guild_id,character_id,kind,metadata) values(v_guild,p_character_id,'leadership_transferred',jsonb_build_object('target',p_target_character_id));
 insert into public.guild_audit_log(guild_id,actor_character_id,target_character_id,action,metadata) values(v_guild,p_character_id,p_target_character_id,'leadership_transfer',jsonb_build_object('previous_target_role',v_target_role));
end;$$;

-- Every privileged function is callable only through server-side service_role/Edge Functions.
revoke all on function public.phase4_storage_cap(uuid) from public,anon,authenticated;
revoke all on function public.phase4_offline_cap_hours(uuid) from public,anon,authenticated;
revoke all on function public.phase4_ensure_bastion(uuid) from public,anon,authenticated;
revoke all on function public.phase4_settle_bastion(uuid) from public,anon,authenticated;
revoke all on function public.phase4_bastion_upgrade(uuid,text) from public,anon,authenticated;
revoke all on function public.phase4_bastion_claim(uuid) from public,anon,authenticated;
revoke all on function public.phase4_activate_altar(uuid) from public,anon,authenticated;
revoke all on function public.phase4_ensure_clan_week(uuid) from public,anon,authenticated;
revoke all on function public.phase4_clan_role(uuid,uuid) from public,anon,authenticated;
revoke all on function public.phase4_clan_donate(uuid,integer,text,integer) from public,anon,authenticated;
revoke all on function public.phase4_clan_research(uuid,text) from public,anon,authenticated;
revoke all on function public.phase4_clan_activate_buff(uuid,text) from public,anon,authenticated;
revoke all on function public.phase4_clan_claim_mission(uuid) from public,anon,authenticated;
revoke all on function public.phase4_clan_shop_buy(uuid,text) from public,anon,authenticated;
revoke all on function public.phase4_war_score(uuid) from public,anon,authenticated;
revoke all on function public.phase4_ensure_war(uuid) from public,anon,authenticated;
revoke all on function public.add_guild_progress(uuid,text,integer,integer) from public,anon,authenticated;
revoke all on function public.clan_raid_attack(uuid) from public,anon,authenticated;
revoke all on function public.clan_set_role(uuid,uuid,text) from public,anon,authenticated;
revoke all on function public.clan_kick(uuid,uuid) from public,anon,authenticated;
revoke all on function public.clan_transfer_leadership(uuid,uuid) from public,anon,authenticated;

grant execute on function public.phase4_storage_cap(uuid),public.phase4_offline_cap_hours(uuid),public.phase4_ensure_bastion(uuid),public.phase4_settle_bastion(uuid),public.phase4_bastion_upgrade(uuid,text),public.phase4_bastion_claim(uuid),public.phase4_activate_altar(uuid),public.phase4_ensure_clan_week(uuid),public.phase4_clan_role(uuid,uuid),public.phase4_clan_donate(uuid,integer,text,integer),public.phase4_clan_research(uuid,text),public.phase4_clan_activate_buff(uuid,text),public.phase4_clan_claim_mission(uuid),public.phase4_clan_shop_buy(uuid,text),public.phase4_war_score(uuid),public.phase4_ensure_war(uuid),public.add_guild_progress(uuid,text,integer,integer),public.clan_raid_attack(uuid),public.clan_set_role(uuid,uuid,text),public.clan_kick(uuid,uuid),public.clan_transfer_leadership(uuid,uuid) to service_role;
