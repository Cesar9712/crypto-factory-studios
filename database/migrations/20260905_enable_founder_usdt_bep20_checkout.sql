alter table public.founder_pack_config add column if not exists payment_config jsonb not null default '{}'::jsonb;
alter table public.founder_pack_orders add column if not exists payment_amount_raw numeric;
alter table public.founder_pack_orders add column if not exists payment_confirmations integer;
alter table public.founder_pack_orders add column if not exists verified_at timestamptz;

create unique index if not exists founder_pack_orders_payment_reference_unique
on public.founder_pack_orders (lower(payment_reference))
where payment_reference is not null;

update public.founder_pack_config
set checkout_enabled = true,
    payment_config = jsonb_build_object(
      'network','BNB Smart Chain',
      'chain_id',56,
      'asset','USDT',
      'standard','BEP20',
      'token_contract','0x55d398326f99059fF775485246999027B3197955',
      'recipient','0xb6e727732F845bDb7792C075B147658e84a173d2',
      'decimals',18,
      'min_confirmations',3
    ),
    updated_at = now()
where pack_key = 'rift_founder';
