-- Security hardening for server-authoritative RPC helpers.
create or replace function public.current_game_week()
returns date language sql stable set search_path=public as $$ select date_trunc('week',timezone('utc',now()))::date $$;
create or replace function public.promote_rarity(p_rarity text)
returns text language sql immutable set search_path=public as $$ select case upper(coalesce(p_rarity,'COMMON')) when 'COMMON' then 'UNCOMMON' when 'UNCOMMON' then 'RARE' when 'RARE' then 'EPIC' when 'EPIC' then 'LEGENDARY' when 'LEGENDARY' then 'MYTHIC' else 'MYTHIC' end $$;

revoke execute on function public.allocate_profession_talent(uuid,text) from public,anon,authenticated;
revoke execute on function public.profession_effect(uuid,text,text) from public,anon,authenticated;
revoke execute on function public.apply_gathering_bonus_drops() from public,anon,authenticated;
revoke execute on function public.apply_gathering_talents() from public,anon,authenticated;
revoke execute on function public.apply_profession_xp_talents() from public,anon,authenticated;
revoke execute on function public.apply_smithing_craft_talents() from public,anon,authenticated;
revoke execute on function public.apply_smithing_enhance_talents() from public,anon,authenticated;
revoke execute on function public.guild_progress_from_craft() from public,anon,authenticated;
revoke execute on function public.guild_progress_from_expedition() from public,anon,authenticated;
revoke execute on function public.guild_progress_from_transaction() from public,anon,authenticated;
grant execute on function public.allocate_profession_talent(uuid,text) to service_role;
grant execute on function public.profession_effect(uuid,text,text) to service_role;
