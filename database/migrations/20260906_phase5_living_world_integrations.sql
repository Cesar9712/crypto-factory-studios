begin;

create or replace function public.phase5_accrue_bonus(p_character uuid,p_bonus_key text,p_resource text,p_amount numeric)
returns bigint language plpgsql security definer set search_path=public as $$
declare v_total numeric;v_whole bigint;
begin
  if p_amount<=0 then return 0; end if;
  insert into public.pet_bonus_bank(character_id,bonus_key,resource_key,amount,updated_at) values(p_character,p_bonus_key,p_resource,p_amount,now())
  on conflict(character_id,bonus_key,resource_key) do update set amount=public.pet_bonus_bank.amount+excluded.amount,updated_at=now()
  returning amount into v_total;
  v_whole:=floor(v_total)::bigint;
  if v_whole>0 then
    update public.pet_bonus_bank set amount=amount-v_whole,updated_at=now() where character_id=p_character and bonus_key=p_bonus_key and resource_key=p_resource;
    if p_resource='xp' then update public.characters set xp=xp+v_whole,updated_at=now() where id=p_character;
    else insert into public.resources(character_id,resource_key,amount) values(p_character,p_resource,v_whole) on conflict(character_id,resource_key) do update set amount=public.resources.amount+excluded.amount; end if;
  end if;
  return v_whole;
end$$;

create or replace function public.phase5_transaction_bonus_hook()
returns trigger language plpgsql security definer set search_path=public as $$
declare v_pct numeric;v_event numeric;v_key text;v_val numeric;v_xp numeric;
begin
  if new.kind='gather' then
    v_pct:=public.phase5_pet_bonus(new.character_id,'gathering');
    v_event:=public.phase5_event_bonus('gathering');
    for v_key,v_val in select key,value::numeric from jsonb_each_text(new.delta) where key in('ore','wood','fish','essence') and value::numeric>0 loop
      perform public.phase5_accrue_bonus(new.character_id,'gathering',v_key,v_val*(coalesce(v_pct,0)+coalesce(v_event,0)));
    end loop;
    perform public.phase5_pet_add_xp(new.character_id,5,'gather:'||new.id::text);
  end if;
  if new.delta ? 'xp' then
    v_xp:=greatest(0,coalesce((new.delta->>'xp')::numeric,0));
    if v_xp>0 then perform public.phase5_accrue_bonus(new.character_id,'xp','xp',v_xp*public.phase5_pet_bonus(new.character_id,'xp')); end if;
  end if;
  return new;
end$$;
drop trigger if exists trg_phase5_transaction_bonus on public.game_transactions;
create trigger trg_phase5_transaction_bonus after insert on public.game_transactions for each row execute function public.phase5_transaction_bonus_hook();

create or replace function public.phase5_crafting_bonus_hook()
returns trigger language plpgsql security definer set search_path=public as $$
declare v_pct numeric;v_cost jsonb;v_key text;v_val numeric;
begin
  v_pct:=public.phase5_pet_bonus(new.character_id,'crafting');
  if v_pct>0 then
    select cost into v_cost from public.crafting_recipes where id=new.recipe_id;
    for v_key,v_val in select key,value::numeric from jsonb_each_text(coalesce(v_cost,'{}'::jsonb)) where key in('ore','wood','fish','essence') and value::numeric>0 loop
      perform public.phase5_accrue_bonus(new.character_id,'crafting',v_key,v_val*v_pct);
    end loop;
  end if;
  perform public.phase5_pet_add_xp(new.character_id,15,'craft:'||new.id::text);
  return new;
end$$;
drop trigger if exists trg_phase5_crafting_bonus on public.crafting_log;
create trigger trg_phase5_crafting_bonus after insert on public.crafting_log for each row execute function public.phase5_crafting_bonus_hook();

create or replace function public.phase5_rift_pet_hook()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  if new.status='completed' and old.status is distinct from new.status then
    perform public.phase5_pet_add_xp(new.character_id,60+greatest(new.tier,1)*10,'rift:'||new.id::text);
    perform public.phase5_try_pet_drop(new.character_id,'rift',new.tier::text,'rift:'||new.id::text);
  end if;
  return new;
end$$;
drop trigger if exists trg_phase5_rift_pet on public.phase2_rift_runs;
create trigger trg_phase5_rift_pet after update of status on public.phase2_rift_runs for each row execute function public.phase5_rift_pet_hook();

create or replace function public.phase5_quest_pet_hook()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  if new.claimed_at is not null and old.claimed_at is null then
    perform public.phase5_pet_add_xp(new.character_id,30,'quest:'||new.quest_id||':'||new.character_id::text);
    perform public.phase5_try_pet_drop(new.character_id,'quest',new.quest_id,'quest:'||new.quest_id||':'||new.character_id::text);
  end if;
  return new;
end$$;
drop trigger if exists trg_phase5_quest_pet on public.quest_progress;
create trigger trg_phase5_quest_pet after update of claimed_at on public.quest_progress for each row execute function public.phase5_quest_pet_hook();

create or replace function public.phase5_world_boss_pet_hook()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  if new.claimed_at is not null and old.claimed_at is null then
    perform public.phase5_pet_add_xp(new.character_id,100,'worldboss:'||new.event_id||':'||new.character_id::text);
    perform public.phase5_try_pet_drop(new.character_id,'world_boss',new.event_id,'worldboss:'||new.event_id||':'||new.character_id::text);
  end if;
  return new;
end$$;
drop trigger if exists trg_phase5_world_boss_pet on public.world_event_contributions;
create trigger trg_phase5_world_boss_pet after update of claimed_at on public.world_event_contributions for each row execute function public.phase5_world_boss_pet_hook();

create or replace function public.phase5_clan_boss_pet_hook()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  if new.claimed_at is not null and old.claimed_at is null then
    perform public.phase5_pet_add_xp(new.character_id,80,'clanboss:'||new.guild_id::text||':'||new.week_start::text||':'||new.character_id::text);
    perform public.phase5_try_pet_drop(new.character_id,'clan_boss',new.guild_id::text,'clanboss:'||new.guild_id::text||':'||new.week_start::text||':'||new.character_id::text);
  end if;
  return new;
end$$;
drop trigger if exists trg_phase5_clan_boss_pet on public.guild_raid_contributions;
create trigger trg_phase5_clan_boss_pet after update of claimed_at on public.guild_raid_contributions for each row execute function public.phase5_clan_boss_pet_hook();

create or replace function public.phase5_codex_progress_hook()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  if tg_op='INSERT' or new.kills>old.kills then perform public.phase5_sync_codex(new.character_id); end if;
  return new;
end$$;
drop trigger if exists trg_phase5_codex_progress on public.monster_codex;
create trigger trg_phase5_codex_progress after insert or update of kills on public.monster_codex for each row execute function public.phase5_codex_progress_hook();

create or replace function public.damage_world_event(p_event_id text,p_character_id uuid,p_damage bigint)
returns table(current_hp bigint,applied_damage bigint) language plpgsql security definer set search_path=public as $$
declare before_hp bigint;dealt bigint;v_mult numeric:=1;
begin
  select we.current_hp into before_hp from public.world_events as we where we.id=p_event_id and we.status='active' for update;
  if before_hp is null then raise exception 'world_event_not_active'; end if;
  v_mult:=1+coalesce(public.phase5_pet_bonus(p_character_id,'boss_damage'),0)+coalesce(public.phase5_event_bonus('boss_damage'),0);
  dealt:=least(greatest(floor(p_damage*v_mult)::bigint,0),before_hp);
  update public.world_events as we set current_hp=greatest(0,we.current_hp-dealt),status=case when we.current_hp-dealt<=0 then 'defeated' else we.status end where we.id=p_event_id returning we.current_hp into current_hp;
  insert into public.world_event_contributions(event_id,character_id,damage,attempts,updated_at) values(p_event_id,p_character_id,dealt,1,now())
  on conflict(event_id,character_id) do update set damage=public.world_event_contributions.damage+excluded.damage,attempts=public.world_event_contributions.attempts+1,updated_at=now();
  applied_damage:=dealt;return next;
end$$;

create or replace function public.clan_raid_attack(p_character_id uuid)
returns table(applied_damage bigint,remaining_hp bigint,defeated boolean) language plpgsql security definer set search_path=public as $$
declare v_guild uuid;v_week date:=public.current_game_week();v_energy integer;v_max_energy integer;v_last timestamptz;v_loc text;v_minutes integer;v_rate integer;v_level integer;v_atk integer;v_crit numeric;v_eqatk integer;v_damage bigint;v_hp bigint;v_research integer:=0;v_mult numeric:=1;
begin
 select guild_id into v_guild from public.guild_members where character_id=p_character_id;if v_guild is null then raise exception 'Not in a clan';end if;perform public.ensure_guild_week(v_guild);perform public.phase4_ensure_clan_week(v_guild);select energy,max_energy,last_tick,location,level into v_energy,v_max_energy,v_last,v_loc,v_level from public.characters where id=p_character_id for update;if v_energy is null then raise exception 'Character not found';end if;v_minutes:=greatest(0,floor(extract(epoch from(now()-coalesce(v_last,now())))/60)::integer);v_rate:=case when v_loc='bastion' then 2 else 1 end;if v_minutes>0 then v_energy:=least(v_max_energy,v_energy+v_minutes*v_rate);update public.characters set energy=v_energy,last_tick=coalesce(v_last,now())+(v_minutes||' minutes')::interval where id=p_character_id;end if;if v_energy<18 then raise exception 'Not enough energy: need 18';end if;
 select atk,crit into v_atk,v_crit from public.character_stats where character_id=p_character_id;select coalesce(sum(ii.atk),0)::integer into v_eqatk from public.equipment e left join public.item_instances ii on ii.id in(e.weapon_item_id,e.helmet_item_id,e.armor_item_id,e.gloves_item_id,e.boots_item_id,e.ring_item_id) where e.character_id=p_character_id;select current_hp into v_hp from public.guild_raids where guild_id=v_guild and week_start=v_week and status='active' for update;if v_hp is null or v_hp<=0 then raise exception 'Clan raid is not active';end if;select level into v_research from public.guild_research where guild_id=v_guild and research_key='boss_damage';v_mult:=1+coalesce(v_research,0)*0.02;if exists(select 1 from public.guild_buffs where guild_id=v_guild and buff_key='boss_fury' and expires_at>now()) then v_mult:=v_mult+0.05;end if;v_mult:=v_mult+coalesce(public.phase5_pet_bonus(p_character_id,'boss_damage'),0)+coalesce(public.phase5_event_bonus('boss_damage'),0);v_damage:=greatest(30,floor(((coalesce(v_atk,10)+coalesce(v_eqatk,0)+v_level*2)*2+floor(random()*35))*v_mult)::bigint);if random()<coalesce(v_crit,0) then v_damage:=floor(v_damage*1.5);end if;v_damage:=least(v_damage,v_hp);
 update public.characters set energy=v_energy-18 where id=p_character_id;update public.guild_raids set current_hp=greatest(0,current_hp-v_damage),status=case when current_hp-v_damage<=0 then 'defeated' else status end,updated_at=now() where guild_id=v_guild and week_start=v_week returning current_hp into v_hp;insert into public.guild_raid_contributions(guild_id,week_start,character_id,damage,attempts,updated_at) values(v_guild,v_week,p_character_id,v_damage,1,now()) on conflict(guild_id,week_start,character_id) do update set damage=public.guild_raid_contributions.damage+excluded.damage,attempts=public.guild_raid_contributions.attempts+1,updated_at=now();update public.guild_members set contribution_points=contribution_points+5,weekly_points=weekly_points+5,shop_credits=shop_credits+5 where guild_id=v_guild and character_id=p_character_id;if v_hp<=0 then update public.guilds set xp=xp+100,level=least(20,1+floor(sqrt((xp+100)::numeric/250.0))::integer),updated_at=now() where id=v_guild;end if;perform public.phase4_ensure_war(v_guild);return query select v_damage,v_hp,v_hp<=0;
end$$;

revoke all on function public.phase5_accrue_bonus(uuid,text,text,numeric),public.phase5_transaction_bonus_hook(),public.phase5_crafting_bonus_hook(),public.phase5_rift_pet_hook(),public.phase5_quest_pet_hook(),public.phase5_world_boss_pet_hook(),public.phase5_clan_boss_pet_hook(),public.phase5_codex_progress_hook(),public.damage_world_event(text,uuid,bigint),public.clan_raid_attack(uuid) from public,anon,authenticated;
grant execute on function public.phase5_accrue_bonus(uuid,text,text,numeric),public.phase5_transaction_bonus_hook(),public.phase5_crafting_bonus_hook(),public.phase5_rift_pet_hook(),public.phase5_quest_pet_hook(),public.phase5_world_boss_pet_hook(),public.phase5_clan_boss_pet_hook(),public.phase5_codex_progress_hook(),public.damage_world_event(text,uuid,bigint),public.clan_raid_attack(uuid) to service_role;

commit;
