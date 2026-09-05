create table if not exists public.founder_pack_config (
  pack_key text primary key,
  name text not null,
  name_es text not null,
  price_usd_cents integer not null check (price_usd_cents > 0),
  internal_value_usd_cents integer not null check (internal_value_usd_cents >= price_usd_cents),
  active boolean not null default true,
  checkout_enabled boolean not null default false,
  benefits jsonb not null default '{}'::jsonb,
  allocation jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.founder_pack_orders (
  id uuid primary key default gen_random_uuid(),
  character_id uuid not null references public.characters(id) on delete cascade,
  pack_key text not null references public.founder_pack_config(pack_key),
  status text not null default 'reserved' check (status in ('reserved','awaiting_payment','paid','cancelled','refunded')),
  price_usd_cents integer not null,
  payment_network text,
  payment_asset text,
  payment_reference text,
  created_at timestamptz not null default now(),
  paid_at timestamptz,
  fulfilled_at timestamptz,
  unique(character_id, pack_key)
);

create table if not exists public.treasury_ledger (
  id bigint generated always as identity primary key,
  source_type text not null,
  source_id uuid,
  gross_usd_cents integer not null check (gross_usd_cents >= 0),
  reward_reserve_cents integer not null default 0 check (reward_reserve_cents >= 0),
  development_cents integer not null default 0 check (development_cents >= 0),
  operations_cents integer not null default 0 check (operations_cents >= 0),
  created_at timestamptz not null default now()
);

alter table public.characters add column if not exists founder_pack_owned boolean not null default false;
alter table public.characters add column if not exists founder_title_unlocked boolean not null default false;
alter table public.characters add column if not exists founder_frame_unlocked boolean not null default false;

alter table public.founder_pack_config enable row level security;
alter table public.founder_pack_orders enable row level security;
alter table public.treasury_ledger enable row level security;

revoke all on public.founder_pack_config from public, anon, authenticated;
revoke all on public.founder_pack_orders from public, anon, authenticated;
revoke all on public.treasury_ledger from public, anon, authenticated;
grant select, insert, update, delete on public.founder_pack_config to service_role;
grant select, insert, update, delete on public.founder_pack_orders to service_role;
grant select, insert on public.treasury_ledger to service_role;

insert into public.founder_pack_config(pack_key,name,name_es,price_usd_cents,internal_value_usd_cents,active,checkout_enabled,benefits,allocation)
values (
  'rift_founder','Rift Founder Pack','Pack Fundador de la Grieta',2000,3500,true,false,
  jsonb_build_object(
    'battle_pass_premium', true,
    'premium_credits', 750,
    'stat_points', 1,
    'profession_tree_points', 1,
    'founder_title', true,
    'founder_frame', true,
    'item', jsonb_build_object('name','Sello del Fundador','rarity','EPIC','slot','ring','atk',2,'def',2)
  ),
  jsonb_build_object('reward_reserve_pct',30,'development_pct',40,'operations_pct',30)
)
on conflict (pack_key) do update set
  name=excluded.name,
  name_es=excluded.name_es,
  price_usd_cents=excluded.price_usd_cents,
  internal_value_usd_cents=excluded.internal_value_usd_cents,
  active=excluded.active,
  benefits=excluded.benefits,
  allocation=excluded.allocation,
  updated_at=now();

create or replace function public.fulfill_founder_pack(p_order uuid, p_payment_reference text default null)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_order founder_pack_orders%rowtype;
  v_pack founder_pack_config%rowtype;
  v_benefits jsonb;
  v_season battle_pass_seasons%rowtype;
  v_stat integer;
  v_prof integer;
  v_credits integer;
  v_reward integer;
  v_dev integer;
  v_ops integer;
begin
  select * into v_order from founder_pack_orders where id=p_order for update;
  if not found then raise exception 'Founder order not found'; end if;
  if v_order.status='paid' and v_order.fulfilled_at is not null then return; end if;
  select * into v_pack from founder_pack_config where pack_key=v_order.pack_key;
  if not found then raise exception 'Founder pack not found'; end if;
  v_benefits := v_pack.benefits;
  v_credits := coalesce((v_benefits->>'premium_credits')::int,0);
  v_stat := coalesce((v_benefits->>'stat_points')::int,0);
  v_prof := coalesce((v_benefits->>'profession_tree_points')::int,0);

  update characters
     set premium_credits_demo = premium_credits_demo + v_credits,
         profession_tree_bonus_points = profession_tree_bonus_points + v_prof,
         founder_pack_owned = true,
         founder_title_unlocked = coalesce((v_benefits->>'founder_title')::boolean,false) or founder_title_unlocked,
         founder_frame_unlocked = coalesce((v_benefits->>'founder_frame')::boolean,false) or founder_frame_unlocked
   where id=v_order.character_id;

  if v_stat > 0 then
    update character_stats set unspent_points = unspent_points + v_stat where character_id=v_order.character_id;
  end if;

  select * into v_season from battle_pass_seasons
   where active=true and starts_at<=now() and ends_at>now()
   order by starts_at desc limit 1;
  if found and coalesce((v_benefits->>'battle_pass_premium')::boolean,false) then
    insert into battle_pass_progress(character_id,season_id,premium_unlocked)
    values(v_order.character_id,v_season.id,true)
    on conflict (character_id,season_id) do update set premium_unlocked=true, updated_at=now();
  end if;

  if v_benefits ? 'item' then
    insert into item_instances(owner_character_id,custom_name,rarity,atk,def,enhancement_level,metadata)
    values(
      v_order.character_id,
      coalesce(v_benefits#>>'{item,name}','Sello del Fundador'),
      coalesce(v_benefits#>>'{item,rarity}','EPIC'),
      coalesce((v_benefits#>>'{item,atk}')::int,0),
      coalesce((v_benefits#>>'{item,def}')::int,0),
      0,
      jsonb_build_object('type','gear','slot',coalesce(v_benefits#>>'{item,slot}','ring'),'founder_pack',true,'cosmetic','founder','value',250)
    );
  end if;

  v_reward := round(v_order.price_usd_cents * coalesce((v_pack.allocation->>'reward_reserve_pct')::numeric,0) / 100.0);
  v_dev := round(v_order.price_usd_cents * coalesce((v_pack.allocation->>'development_pct')::numeric,0) / 100.0);
  v_ops := v_order.price_usd_cents - v_reward - v_dev;

  update founder_pack_orders
     set status='paid', payment_reference=coalesce(p_payment_reference,payment_reference), paid_at=coalesce(paid_at,now()), fulfilled_at=now()
   where id=p_order;

  if not exists(select 1 from treasury_ledger where source_type='founder_pack' and source_id=p_order) then
    insert into treasury_ledger(source_type,source_id,gross_usd_cents,reward_reserve_cents,development_cents,operations_cents)
    values('founder_pack',p_order,v_order.price_usd_cents,v_reward,v_dev,v_ops);
  end if;
end;
$$;

revoke all on function public.fulfill_founder_pack(uuid,text) from public, anon, authenticated;
grant execute on function public.fulfill_founder_pack(uuid,text) to service_role;
