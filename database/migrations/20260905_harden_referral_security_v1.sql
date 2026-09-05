create or replace function public.referral_code_for_character(p_character uuid)
returns text
language sql
immutable
set search_path = public
as $$
  select 'NX' || upper(substr(replace(p_character::text,'-',''),1,10));
$$;

revoke all on function public.referral_code_for_character(uuid) from public, anon, authenticated;
grant execute on function public.referral_code_for_character(uuid) to service_role;

revoke all on function public.handle_referral_founder_paid() from public, anon, authenticated;
