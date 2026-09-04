-- Profession talent trees + combat profession (Rift Hunter / Cazador de Grietas)
-- Real-money systems remain disabled; all rewards below are internal game progression.

alter table public.profession_progress drop constraint if exists profession_progress_profession_key_check;
alter table public.profession_progress add constraint profession_progress_profession_key_check
  check (profession_key in ('mining','woodcutting','fishing','smithing','hunter'));

create table if not exists public.profession_talent_definitions (
  id text primary key,
  profession_key text not null check (profession_key in ('mining','woodcutting','fishing','smithing','hunter')),
  name text not null,
  description text not null default '',
  branch text not null default 'core',
  tier integer not null default 1 check (tier between 1 and 10),
  position integer not null default 1,
  max_rank integer not null default 5 check (max_rank between 1 and 10),
  required_profession_level integer not null default 1 check (required_profession_level between 1 and 100),
  prerequisite_id text,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.profession_talent_progress (
  character_id uuid not null references public.characters(id) on delete cascade,
  talent_id text not null references public.profession_talent_definitions(id) on delete cascade,
  rank integer not null default 0 check (rank between 0 and 10),
  updated_at timestamptz not null default now(),
  primary key (character_id, talent_id)
);

create table if not exists public.hunt_assignments (
  id uuid primary key default gen_random_uuid(),
  character_id uuid not null references public.characters(id) on delete cascade,
  enemy_id text not null references public.enemy_definitions(id) on delete cascade,
  target_count integer not null check (target_count > 0),
  progress integer not null default 0 check (progress >= 0),
  status text not null default 'active' check (status in ('active','completed','abandoned')),
  assigned_at timestamptz not null default now(),
  completed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);
create unique index if not exists hunt_assignments_one_active_per_character on public.hunt_assignments(character_id) where status='active';
create index if not exists hunt_assignments_character_history on public.hunt_assignments(character_id,assigned_at desc);

alter table public.profession_talent_definitions enable row level security;
alter table public.profession_talent_progress enable row level security;
alter table public.hunt_assignments enable row level security;

drop policy if exists profession_talent_definitions_read on public.profession_talent_definitions;
create policy profession_talent_definitions_read on public.profession_talent_definitions for select to authenticated using (true);
drop policy if exists profession_talent_progress_read_own on public.profession_talent_progress;
create policy profession_talent_progress_read_own on public.profession_talent_progress for select to authenticated using (exists(select 1 from public.characters c where c.id=character_id and c.user_id=auth.uid()));
drop policy if exists hunt_assignments_read_own on public.hunt_assignments;
create policy hunt_assignments_read_own on public.hunt_assignments for select to authenticated using (exists(select 1 from public.characters c where c.id=character_id and c.user_id=auth.uid()));

insert into public.profession_progress(character_id,profession_key,level,xp,updated_at)
select id,'hunter',1,0,now() from public.characters
on conflict(character_id,profession_key) do nothing;

-- Six functional nodes per profession. effect_key/effect_value are consumed by server-side triggers/engines.
insert into public.profession_talent_definitions(id,profession_key,name,description,branch,tier,position,max_rank,required_profession_level,prerequisite_id,metadata) values
('mining_rich_veins','mining','Rich Veins','Extract more ore from every successful mining action.','prospector',1,1,5,1,null,'{"name_es":"Vetas Ricas","description_es":"Extrae más mineral en cada acción de minería.","effect_key":"yield_flat","effect_value":1,"icon":"⛏️"}'),
('mining_training','mining','Field Training','Gain more Mining profession XP.','mastery',1,2,5,1,null,'{"name_es":"Entrenamiento de Campo","description_es":"Aumenta la XP de profesión de Minería.","effect_key":"xp_pct","effect_value":5,"icon":"📘"}'),
('mining_precision','mining','Precision Extraction','Increase ore yield proportionally.','prospector',2,1,5,5,'mining_rich_veins','{"name_es":"Extracción Precisa","description_es":"Aumenta porcentualmente la cantidad de mineral obtenido.","effect_key":"yield_pct","effect_value":4,"icon":"🎯"}'),
('mining_deep_echo','mining','Deep Echo','Chance to discover Essence while mining.','mastery',2,2,5,5,'mining_training','{"name_es":"Eco Profundo","description_es":"Probabilidad de encontrar Esencia al minar.","effect_key":"essence_chance","effect_value":0.02,"icon":"✨"}'),
('mining_double_vein','mining','Twin Vein','Chance to double the base mining yield.','prospector',3,1,5,12,'mining_precision','{"name_es":"Veta Gemela","description_es":"Probabilidad de duplicar la extracción base.","effect_key":"double_chance","effect_value":0.025,"icon":"💎"}'),
('mining_master','mining','Master Prospector','Adds further flat ore yield at high profession level.','mastery',3,2,3,15,'mining_deep_echo','{"name_es":"Maestro Prospector","description_es":"Añade aún más mineral por extracción.","effect_key":"yield_flat","effect_value":1,"icon":"👑"}'),
('wood_abundance','woodcutting','Abundant Cuts','Gather more wood per action.','harvest',1,1,5,1,null,'{"name_es":"Cortes Abundantes","description_es":"Obtén más madera por acción.","effect_key":"yield_flat","effect_value":1,"icon":"🪓"}'),
('wood_training','woodcutting','Woodland Training','Gain more Woodcutting profession XP.','mastery',1,2,5,1,null,'{"name_es":"Entrenamiento Forestal","description_es":"Aumenta la XP de profesión de Leñador.","effect_key":"xp_pct","effect_value":5,"icon":"📘"}'),
('wood_clean_cuts','woodcutting','Clean Cuts','Increase wood yield proportionally.','harvest',2,1,5,5,'wood_abundance','{"name_es":"Cortes Limpios","description_es":"Aumenta porcentualmente la madera obtenida.","effect_key":"yield_pct","effect_value":4,"icon":"🌲"}'),
('wood_resin','woodcutting','Arcane Resin','Chance to find Essence while gathering wood.','mastery',2,2,5,5,'wood_training','{"name_es":"Resina Arcana","description_es":"Probabilidad de encontrar Esencia al talar.","effect_key":"essence_chance","effect_value":0.02,"icon":"✨"}'),
('wood_twin_fall','woodcutting','Twin Fall','Chance to double the base wood yield.','harvest',3,1,5,12,'wood_clean_cuts','{"name_es":"Doble Caída","description_es":"Probabilidad de duplicar la madera base.","effect_key":"double_chance","effect_value":0.025,"icon":"🌳"}'),
('wood_master','woodcutting','Master Lumberjack','Adds further flat wood yield.','mastery',3,2,3,15,'wood_resin','{"name_es":"Maestro Leñador","description_es":"Añade aún más madera por acción.","effect_key":"yield_flat","effect_value":1,"icon":"👑"}'),
('fish_big_catch','fishing','Big Catch','Catch more fish per action.','catch',1,1,5,1,null,'{"name_es":"Gran Captura","description_es":"Captura más peces por acción.","effect_key":"yield_flat","effect_value":1,"icon":"🎣"}'),
('fish_training','fishing','Angler Training','Gain more Fishing profession XP.','mastery',1,2,5,1,null,'{"name_es":"Entrenamiento de Pescador","description_es":"Aumenta la XP de profesión de Pesca.","effect_key":"xp_pct","effect_value":5,"icon":"📘"}'),
('fish_school','fishing','School Reader','Increase fish yield proportionally.','catch',2,1,5,5,'fish_big_catch','{"name_es":"Lector de Cardúmenes","description_es":"Aumenta porcentualmente la pesca obtenida.","effect_key":"yield_pct","effect_value":4,"icon":"🐟"}'),
('fish_pearl','fishing','Rift Pearl','Chance to fish up Essence.','mastery',2,2,5,5,'fish_training','{"name_es":"Perla de Grieta","description_es":"Probabilidad de obtener Esencia al pescar.","effect_key":"essence_chance","effect_value":0.025,"icon":"✨"}'),
('fish_double_hook','fishing','Double Hook','Chance to double the base catch.','catch',3,1,5,12,'fish_school','{"name_es":"Anzuelo Doble","description_es":"Probabilidad de duplicar la captura base.","effect_key":"double_chance","effect_value":0.03,"icon":"🪝"}'),
('fish_treasure','fishing','Treasure Current','Chance to find a small amount of internal Gold while fishing.','mastery',3,2,5,15,'fish_pearl','{"name_es":"Corriente del Tesoro","description_es":"Probabilidad de encontrar una pequeña cantidad de Oro interno al pescar.","effect_key":"treasure_gold_chance","effect_value":0.03,"icon":"🪙"}'),
('smith_training','smithing','Forge Discipline','Gain more Smithing profession XP.','mastery',1,1,5,1,null,'{"name_es":"Disciplina de Forja","description_es":"Aumenta la XP de profesión de Herrería.","effect_key":"xp_pct","effect_value":5,"icon":"📘"}'),
('smith_temper','smithing','Weapon Tempering','Crafted weapons gain additional ATK.','weapons',1,2,5,1,null,'{"name_es":"Temple de Armas","description_es":"Las armas fabricadas obtienen ATQ adicional.","effect_key":"crafted_atk_flat","effect_value":1,"icon":"⚔️"}'),
('smith_reinforce','smithing','Armor Reinforcement','Crafted defensive gear gains additional DEF.','armor',1,3,5,1,null,'{"name_es":"Refuerzo de Armadura","description_es":"El equipo defensivo fabricado obtiene DEF adicional.","effect_key":"crafted_def_flat","effect_value":1,"icon":"🛡️"}'),
('smith_masterwork','smithing','Masterwork','Chance for a crafted item to improve one rarity tier.','mastery',2,1,5,6,'smith_training','{"name_es":"Obra Maestra","description_es":"Probabilidad de mejorar una categoría de rareza al fabricar.","effect_key":"masterwork_chance","effect_value":0.03,"icon":"✨"}'),
('smith_enhancement','smithing','Refined Enhancement','Enhancing equipment grants extra stat power.','weapons',2,2,3,8,'smith_temper','{"name_es":"Mejora Refinada","description_es":"Las mejoras de equipo otorgan estadísticas adicionales.","effect_key":"enhance_bonus","effect_value":1,"icon":"🔨"}'),
('smith_legendary','smithing','Legendary Craft','Additional chance to improve crafted item rarity.','armor',3,3,3,18,'smith_reinforce','{"name_es":"Forja Legendaria","description_es":"Probabilidad adicional de mejorar la rareza de lo fabricado.","effect_key":"masterwork_chance","effect_value":0.05,"icon":"👑"}'),
('hunter_training','hunter','Marked Prey Training','Gain more Hunter profession XP from marked kills.','tracking',1,1,5,1,null,'{"name_es":"Entrenamiento de Presa Marcada","description_es":"Aumenta la XP de Cazador obtenida solo al derrotar objetivos asignados.","effect_key":"xp_pct","effect_value":5,"icon":"📘"}'),
('hunter_marked_damage','hunter','Marked Weakness','Deal more damage to your assigned target.','assault',1,2,5,1,null,'{"name_es":"Debilidad Marcada","description_es":"Inflige más daño al objetivo de cacería asignado.","effect_key":"marked_damage_pct","effect_value":3,"icon":"🎯"}'),
('hunter_executioner','hunter','Executioner Instinct','Gain extra critical chance against assigned targets.','assault',2,2,5,5,'hunter_marked_damage','{"name_es":"Instinto Ejecutor","description_es":"Aumenta el crítico contra objetivos de cacería.","effect_key":"marked_crit","effect_value":0.01,"icon":"🗡️"}'),
('hunter_trophies','hunter','Trophy Seeker','Increase loot chance from assigned targets.','tracking',2,1,5,5,'hunter_training','{"name_es":"Buscador de Trofeos","description_es":"Aumenta la probabilidad de botín del objetivo asignado.","effect_key":"marked_loot","effect_value":0.02,"icon":"🏆"}'),
('hunter_efficiency','hunter','Efficient Stalker','Assigned targets cost less Energy to engage.','tracking',3,1,3,10,'hunter_trophies','{"name_es":"Acechador Eficiente","description_es":"Reduce la Energía necesaria para combatir al objetivo asignado.","effect_key":"marked_energy_flat","effect_value":1,"icon":"⚡"}'),
('hunter_apex','hunter','Apex Hunter','Deal additional damage when the assigned target is a boss.','assault',3,2,5,15,'hunter_executioner','{"name_es":"Cazador Alfa","description_es":"Aumenta el daño si el objetivo asignado es un jefe.","effect_key":"boss_damage_pct","effect_value":5,"icon":"👑"}')
on conflict(id) do update set profession_key=excluded.profession_key,name=excluded.name,description=excluded.description,branch=excluded.branch,tier=excluded.tier,position=excluded.position,max_rank=excluded.max_rank,required_profession_level=excluded.required_profession_level,prerequisite_id=excluded.prerequisite_id,metadata=excluded.metadata;

create or replace function public.profession_effect(p_character uuid,p_profession text,p_effect text)
returns numeric language sql stable security definer set search_path=public as $$
select coalesce(sum(ptp.rank*coalesce((ptd.metadata->>'effect_value')::numeric,0)),0)
from public.profession_talent_progress ptp join public.profession_talent_definitions ptd on ptd.id=ptp.talent_id
where ptp.character_id=p_character and ptd.profession_key=p_profession and ptd.metadata->>'effect_key'=p_effect;
$$;

create or replace function public.apply_profession_xp_talents() returns trigger language plpgsql security definer set search_path=public as $$
declare base_delta bigint; bonus_pct numeric;
begin
 if new.xp>old.xp then
  base_delta:=new.xp-old.xp; bonus_pct:=public.profession_effect(new.character_id,new.profession_key,'xp_pct');
  if bonus_pct>0 then new.xp:=old.xp+ceil(base_delta*(1+bonus_pct/100.0)); end if;
  new.level:=least(100,1+floor(new.xp/120.0));
 end if;
 new.updated_at:=now(); return new;
end; $$;
drop trigger if exists trg_profession_xp_talents on public.profession_progress;
create trigger trg_profession_xp_talents before update on public.profession_progress for each row execute function public.apply_profession_xp_talents();

create or replace function public.apply_gathering_talents() returns trigger language plpgsql security definer set search_path=public as $$
declare prof text; delta bigint; flat_bonus numeric; pct_bonus numeric; double_chance numeric;
begin
 if new.amount<=old.amount then return new; end if;
 prof:=case new.resource_key when 'ore' then 'mining' when 'wood' then 'woodcutting' when 'fish' then 'fishing' else null end;
 if prof is null then return new; end if;
 delta:=new.amount-old.amount; flat_bonus:=public.profession_effect(new.character_id,prof,'yield_flat'); pct_bonus:=public.profession_effect(new.character_id,prof,'yield_pct'); double_chance:=public.profession_effect(new.character_id,prof,'double_chance');
 new.amount:=new.amount+floor(flat_bonus)+floor(delta*pct_bonus/100.0); if random()<least(.60,double_chance) then new.amount:=new.amount+delta; end if; return new;
end; $$;
drop trigger if exists trg_gathering_talents on public.resources;
create trigger trg_gathering_talents before update on public.resources for each row execute function public.apply_gathering_talents();

create or replace function public.apply_gathering_bonus_drops() returns trigger language plpgsql security definer set search_path=public as $$
declare prof text; essence_chance numeric; treasure_chance numeric;
begin
 if new.amount<=old.amount then return new; end if;
 prof:=case new.resource_key when 'ore' then 'mining' when 'wood' then 'woodcutting' when 'fish' then 'fishing' else null end; if prof is null then return new; end if;
 essence_chance:=public.profession_effect(new.character_id,prof,'essence_chance'); if essence_chance>0 and random()<least(.50,essence_chance) then insert into public.resources(character_id,resource_key,amount) values(new.character_id,'essence',1) on conflict(character_id,resource_key) do update set amount=public.resources.amount+1; end if;
 if prof='fishing' then treasure_chance:=public.profession_effect(new.character_id,prof,'treasure_gold_chance'); if treasure_chance>0 and random()<least(.50,treasure_chance) then update public.characters set gold=gold+10 where id=new.character_id; end if; end if; return new;
end; $$;
drop trigger if exists trg_gathering_bonus_drops on public.resources;
create trigger trg_gathering_bonus_drops after update on public.resources for each row execute function public.apply_gathering_bonus_drops();

create or replace function public.promote_rarity(p_rarity text) returns text language sql immutable as $$ select case upper(coalesce(p_rarity,'COMMON')) when 'COMMON' then 'UNCOMMON' when 'UNCOMMON' then 'RARE' when 'RARE' then 'EPIC' when 'EPIC' then 'LEGENDARY' when 'LEGENDARY' then 'MYTHIC' else 'MYTHIC' end; $$;

create or replace function public.apply_smithing_craft_talents() returns trigger language plpgsql security definer set search_path=public as $$
declare is_recipe boolean; atk_bonus numeric; def_bonus numeric; masterwork numeric; slot_name text;
begin
 if new.owner_character_id is null or new.custom_name is null then return new; end if; select exists(select 1 from public.crafting_recipes r where r.name=new.custom_name) into is_recipe; if not is_recipe then return new; end if;
 atk_bonus:=public.profession_effect(new.owner_character_id,'smithing','crafted_atk_flat'); def_bonus:=public.profession_effect(new.owner_character_id,'smithing','crafted_def_flat'); masterwork:=public.profession_effect(new.owner_character_id,'smithing','masterwork_chance'); slot_name:=coalesce(new.metadata->>'slot','');
 if slot_name in ('weapon','ring') then new.atk:=coalesce(new.atk,0)+floor(atk_bonus); end if; if slot_name in ('armor','boots','ring') then new.def:=coalesce(new.def,0)+floor(def_bonus); end if; if masterwork>0 and random()<least(.65,masterwork) then new.rarity:=public.promote_rarity(new.rarity); end if; return new;
end; $$;
drop trigger if exists trg_smithing_craft_talents on public.item_instances;
create trigger trg_smithing_craft_talents before insert on public.item_instances for each row execute function public.apply_smithing_craft_talents();

create or replace function public.apply_smithing_enhance_talents() returns trigger language plpgsql security definer set search_path=public as $$
declare bonus numeric;
begin
 if new.enhancement_level<=old.enhancement_level then return new; end if; bonus:=public.profession_effect(new.owner_character_id,'smithing','enhance_bonus'); if bonus<=0 then return new; end if; if new.atk>old.atk then new.atk:=new.atk+floor(bonus); end if; if new.def>old.def then new.def:=new.def+floor(bonus); end if; return new;
end; $$;
drop trigger if exists trg_smithing_enhance_talents on public.item_instances;
create trigger trg_smithing_enhance_talents before update on public.item_instances for each row execute function public.apply_smithing_enhance_talents();

create or replace function public.allocate_profession_talent(p_character uuid,p_talent text)
returns table(talent_id text,new_rank integer,available_points integer)
language plpgsql security definer set search_path=public as $$
declare c_level integer; p_level integer; earned integer; spent integer; cur_rank integer; defrow public.profession_talent_definitions%rowtype; prereq_rank integer;
begin
 select level into c_level from public.characters where id=p_character for update; if c_level is null then raise exception 'Character not found'; end if;
 select * into defrow from public.profession_talent_definitions where id=p_talent; if not found then raise exception 'Unknown talent'; end if;
 select level into p_level from public.profession_progress where character_id=p_character and profession_key=defrow.profession_key; p_level:=coalesce(p_level,1); if p_level<defrow.required_profession_level then raise exception 'Profession level % required',defrow.required_profession_level; end if;
 if defrow.prerequisite_id is not null then select rank into prereq_rank from public.profession_talent_progress where character_id=p_character and talent_id=defrow.prerequisite_id; if coalesce(prereq_rank,0)<1 then raise exception 'Prerequisite talent required'; end if; end if;
 select rank into cur_rank from public.profession_talent_progress where character_id=p_character and talent_id=p_talent; cur_rank:=coalesce(cur_rank,0); if cur_rank>=defrow.max_rank then raise exception 'Talent maxed'; end if;
 earned:=greatest(0,(c_level-1)*2); select coalesce(sum(rank),0)::integer into spent from public.profession_talent_progress where character_id=p_character; if spent>=earned then raise exception 'No profession talent points available'; end if;
 insert into public.profession_talent_progress(character_id,talent_id,rank,updated_at) values(p_character,p_talent,1,now()) on conflict(character_id,talent_id) do update set rank=public.profession_talent_progress.rank+1,updated_at=now();
 cur_rank:=cur_rank+1; available_points:=earned-(spent+1); talent_id:=p_talent; new_rank:=cur_rank; return next;
end; $$;
revoke all on function public.allocate_profession_talent(uuid,text) from public;
grant execute on function public.allocate_profession_talent(uuid,text) to service_role;
