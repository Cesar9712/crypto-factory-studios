create table if not exists public.referral_config (
  id smallint primary key default 1 check (id = 1),
  active boolean not null default true,
  referrer_premium_credits integer not null default 150 check (referrer_premium_credits >= 0),
  referred_premium_credits integer not null default 50 check (referred_premium_credits >= 0),
  attribution_window_days integer not null default 7 check (attribution_window_days between 1 and 90),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

insert into public.referral_config(id,active,referrer_premium_credits,referred_premium_credits,attribution_window_days)
values(1,true,150,50,7)
on conflict (id) do update set
  active=excluded.active,
  referrer_premium_credits=excluded.referrer_premium_credits,
  referred_premium_credits=excluded.referred_premium_credits,
  attribution_window_days=excluded.attribution_window_days,
  updated_at=now();

create table if not exists public.referral_profiles (
  character_id uuid primary key references public.characters(id) on delete cascade,
  code text not null unique check (code ~ '^[A-Z0-9]{6,20}$'),
  created_at timestamptz not null default now()
);

create table if not exists public.referral_attributions (
  referred_character_id uuid primary key references public.characters(id) on delete cascade,
  referrer_character_id uuid not null references public.characters(id) on delete cascade,
  code_used text not null,
  status text not null default 'attached' check (status in ('attached','rewarded','void')),
  created_at timestamptz not null default now(),
  rewarded_at timestamptz,
  constraint referral_not_self check (referred_character_id <> referrer_character_id)
);
create index if not exists referral_attributions_referrer_idx on public.referral_attributions(referrer_character_id,created_at desc);

create table if not exists public.referral_rewards (
  id bigint generated always as identity primary key,
  referrer_character_id uuid not null references public.characters(id) on delete cascade,
  referred_character_id uuid not null references public.characters(id) on delete cascade,
  source_order_id uuid not null unique references public.founder_pack_orders(id) on delete restrict,
  referrer_premium_credits integer not null check (referrer_premium_credits >= 0),
  referred_premium_credits integer not null check (referred_premium_credits >= 0),
  created_at timestamptz not null default now(),
  unique(referred_character_id)
);
create index if not exists referral_rewards_referrer_idx on public.referral_rewards(referrer_character_id,created_at desc);

alter table public.referral_config enable row level security;
alter table public.referral_profiles enable row level security;
alter table public.referral_attributions enable row level security;
alter table public.referral_rewards enable row level security;
revoke all on public.referral_config from public, anon, authenticated;
revoke all on public.referral_profiles from public, anon, authenticated;
revoke all on public.referral_attributions from public, anon, authenticated;
revoke all on public.referral_rewards from public, anon, authenticated;
grant select,insert,update,delete on public.referral_config to service_role;
grant select,insert,update,delete on public.referral_profiles to service_role;
grant select,insert,update,delete on public.referral_attributions to service_role;
grant select,insert on public.referral_rewards to service_role;

create or replace function public.referral_code_for_character(p_character uuid)
returns text
language sql
immutable
as $$
  select 'NX' || upper(substr(replace(p_character::text,'-',''),1,10));
$$;

create or replace function public.ensure_referral_profile(p_character uuid)
returns text
language plpgsql
security definer
set search_path=public
as $$
declare v_code text;
begin
  select code into v_code from referral_profiles where character_id=p_character;
  if v_code is not null then return v_code; end if;
  v_code := referral_code_for_character(p_character);
  insert into referral_profiles(character_id,code) values(p_character,v_code)
  on conflict (character_id) do nothing;
  select code into v_code from referral_profiles where character_id=p_character;
  return v_code;
end;
$$;
revoke all on function public.ensure_referral_profile(uuid) from public,anon,authenticated;
grant execute on function public.ensure_referral_profile(uuid) to service_role;

create or replace function public.apply_referral_code(p_referred uuid,p_code text)
returns void
language plpgsql
security definer
set search_path=public
as $$
declare
  v_referrer uuid;
  v_created timestamptz;
  v_owned boolean;
  v_cfg referral_config%rowtype;
begin
  select * into v_cfg from referral_config where id=1;
  if not found or not v_cfg.active then raise exception 'Referral program disabled'; end if;
  select created_at,founder_pack_owned into v_created,v_owned from characters where id=p_referred for update;
  if not found then raise exception 'Character not found'; end if;
  if v_owned then raise exception 'Referral must be applied before Founder Pack purchase'; end if;
  if now() > v_created + make_interval(days=>v_cfg.attribution_window_days) then raise exception 'Referral attribution window expired'; end if;
  if exists(select 1 from founder_pack_orders where character_id=p_referred and status='paid') then raise exception 'Referral must be applied before Founder Pack purchase'; end if;
  if exists(select 1 from referral_attributions where referred_character_id=p_referred) then raise exception 'Referral already attached'; end if;
  select character_id into v_referrer from referral_profiles where upper(code)=upper(trim(p_code));
  if v_referrer is null then raise exception 'Referral code not found'; end if;
  if v_referrer=p_referred then raise exception 'You cannot refer yourself'; end if;
  insert into referral_attributions(referred_character_id,referrer_character_id,code_used)
  values(p_referred,v_referrer,upper(trim(p_code)));
end;
$$;
revoke all on function public.apply_referral_code(uuid,text) from public,anon,authenticated;
grant execute on function public.apply_referral_code(uuid,text) to service_role;

create or replace function public.handle_referral_founder_paid()
returns trigger
language plpgsql
security definer
set search_path=public
as $$
declare
  v_attr referral_attributions%rowtype;
  v_cfg referral_config%rowtype;
begin
  if new.status <> 'paid' or old.status = 'paid' then return new; end if;
  select * into v_attr from referral_attributions where referred_character_id=new.character_id and status='attached' for update;
  if not found then return new; end if;
  select * into v_cfg from referral_config where id=1;
  if not found or not v_cfg.active then return new; end if;
  if exists(select 1 from referral_rewards where source_order_id=new.id or referred_character_id=new.character_id) then return new; end if;
  update characters set premium_credits_demo=premium_credits_demo+v_cfg.referrer_premium_credits where id=v_attr.referrer_character_id;
  update characters set premium_credits_demo=premium_credits_demo+v_cfg.referred_premium_credits where id=v_attr.referred_character_id;
  insert into referral_rewards(referrer_character_id,referred_character_id,source_order_id,referrer_premium_credits,referred_premium_credits)
  values(v_attr.referrer_character_id,v_attr.referred_character_id,new.id,v_cfg.referrer_premium_credits,v_cfg.referred_premium_credits);
  update referral_attributions set status='rewarded',rewarded_at=now() where referred_character_id=v_attr.referred_character_id;
  return new;
end;
$$;

drop trigger if exists trg_referral_founder_paid on public.founder_pack_orders;
create trigger trg_referral_founder_paid
after update of status on public.founder_pack_orders
for each row execute function public.handle_referral_founder_paid();
