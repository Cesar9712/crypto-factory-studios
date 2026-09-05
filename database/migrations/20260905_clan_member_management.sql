-- Clan leader management helpers used by clan-engine v2.
create or replace function public.clan_set_role(p_character_id uuid,p_target_character_id uuid,p_role text)
returns void language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_role text;
begin
 select guild_id,role into v_guild,v_role from public.guild_members where character_id=p_character_id;
 if v_guild is null or v_role<>'leader' then raise exception 'Leader permission required'; end if;
 if p_target_character_id=p_character_id then raise exception 'Cannot change your own leader role'; end if;
 if p_role not in ('member','officer') then raise exception 'Invalid clan role'; end if;
 if not exists(select 1 from public.guild_members where guild_id=v_guild and character_id=p_target_character_id) then raise exception 'Member not found'; end if;
 update public.guild_members set role=p_role where guild_id=v_guild and character_id=p_target_character_id;
end;$$;
create or replace function public.clan_kick(p_character_id uuid,p_target_character_id uuid)
returns void language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_role text;
begin
 select guild_id,role into v_guild,v_role from public.guild_members where character_id=p_character_id;
 if v_guild is null or v_role<>'leader' then raise exception 'Leader permission required'; end if;
 if p_target_character_id=p_character_id then raise exception 'Leader cannot kick self'; end if;
 delete from public.guild_members where guild_id=v_guild and character_id=p_target_character_id;
end;$$;
create or replace function public.clan_transfer_leadership(p_character_id uuid,p_target_character_id uuid)
returns void language plpgsql security definer set search_path=public as $$
declare v_guild uuid; v_role text;
begin
 select guild_id,role into v_guild,v_role from public.guild_members where character_id=p_character_id for update;
 if v_guild is null or v_role<>'leader' then raise exception 'Leader permission required'; end if;
 if not exists(select 1 from public.guild_members where guild_id=v_guild and character_id=p_target_character_id) then raise exception 'Member not found'; end if;
 update public.guild_members set role='officer' where guild_id=v_guild and character_id=p_character_id;
 update public.guild_members set role='leader' where guild_id=v_guild and character_id=p_target_character_id;
 update public.guilds set owner_character_id=p_target_character_id,updated_at=now() where id=v_guild;
end;$$;
revoke all on function public.clan_set_role(uuid,uuid,text) from public,anon,authenticated;
revoke all on function public.clan_kick(uuid,uuid) from public,anon,authenticated;
revoke all on function public.clan_transfer_leadership(uuid,uuid) from public,anon,authenticated;
grant execute on function public.clan_set_role(uuid,uuid,text) to service_role;
grant execute on function public.clan_kick(uuid,uuid) to service_role;
grant execute on function public.clan_transfer_leadership(uuid,uuid) to service_role;
