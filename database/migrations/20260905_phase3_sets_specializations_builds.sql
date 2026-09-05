-- Nexus Realms Phase 3: equipment sets, six-slot builds and class specializations.
-- All build bonuses and respec/equip actions are server-authoritative.

create table if not exists public.phase3_set_definitions (
  id text primary key,
  name_en text not null,
  name_es text not null,
  class_key text check (class_key is null or class_key in ('warrior','mage','archer','assassin')),
  theme text not null default 'rift',
  bonus_2 jsonb not null default '{}'::jsonb,
  bonus_4 jsonb not null default '{}'::jsonb,
  bonus_6 jsonb not null default '{}'::jsonb,
  recommended_specializations text[] not null default '{}',
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.phase3_specializations (
  id text primary key,
  class_key text not null check (class_key in ('warrior','mage','archer','assassin')),
  name_en text not null,
  name_es text not null,
  description_en text not null,
  description_es text not null,
  unlock_level integer not null default 10 check (unlock_level >= 1),
  stat_modifiers jsonb not null default '{}'::jsonb,
  passive_effects jsonb not null default '{}'::jsonb,
  pvp_modifiers jsonb not null default '{}'::jsonb,
  ai_priority jsonb not null default '{}'::jsonb,
  recommended_set_id text references public.phase3_set_definitions(id) on delete set null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.phase3_specialization_skills (
  id text primary key,
  specialization_id text not null references public.phase3_specializations(id) on delete cascade,
  name text not null,
  name_es text not null,
  kind text not null check (kind in ('damage','guard','execute')),
  mana_cost integer not null default 0 check (mana_cost >= 0),
  multiplier numeric not null default 1 check (multiplier > 0 and multiplier <= 3),
  cooldown_turns integer not null default 2 check (cooldown_turns between 1 and 8),
  damage_reduction numeric not null default 1 check (damage_reduction between 0.15 and 1),
  execute_threshold numeric not null default 0 check (execute_threshold between 0 and 0.6),
  armor_pierce numeric not null default 0 check (armor_pierce between 0 and 0.6),
  crit_bonus numeric not null default 0 check (crit_bonus between 0 and 0.25),
  min_level integer not null default 10 check (min_level >= 10),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.characters add column if not exists specialization text;
alter table public.characters add column if not exists specialization_respec_count integer not null default 0;
alter table public.equipment add column if not exists helmet_item_id uuid references public.item_instances(id) on delete set null;
alter table public.equipment add column if not exists gloves_item_id uuid references public.item_instances(id) on delete set null;
alter table public.item_instances add column if not exists set_id text references public.phase3_set_definitions(id) on delete set null;

create index if not exists phase3_items_set_idx on public.item_instances(set_id) where set_id is not null;
create index if not exists phase3_specs_class_idx on public.phase3_specializations(class_key,active);
create index if not exists phase3_skills_spec_idx on public.phase3_specialization_skills(specialization_id,min_level);
create index if not exists equipment_helmet_idx on public.equipment(helmet_item_id) where helmet_item_id is not null;
create index if not exists equipment_gloves_idx on public.equipment(gloves_item_id) where gloves_item_id is not null;

insert into public.phase3_set_definitions(id,name_en,name_es,class_key,theme,bonus_2,bonus_4,bonus_6,recommended_specializations) values
('ash_lord','Ash Lord','Señor de las Cenizas','warrior','ash','{"damage_pct":0.08}','{"crit_flat":0.06}','{"proc_chance":0.18,"proc_damage_pct":0.30}',array['berserker','gladiator']),
('iron_bastion','Iron Bastion','Bastión de Hierro','warrior','bastion','{"def_pct":0.10}','{"damage_reduction_pct":0.08}','{"def_pct":0.12,"dodge_flat":0.04}',array['guardian']),
('ember_savant','Ember Savant','Sabio de las Brasas','mage','ember','{"skill_damage_pct":0.08}','{"crit_flat":0.04,"damage_pct":0.05}','{"proc_chance":0.16,"proc_damage_pct":0.34}',array['pyromancer','arcanist']),
('frost_weaver','Frost Weaver','Tejedor de Escarcha','mage','frost','{"def_pct":0.07}','{"mana_cost_pct":-0.10}','{"damage_reduction_pct":0.07,"skill_damage_pct":0.10}',array['cryomancer']),
('storm_marksman','Storm Marksman','Tirador de la Tormenta','archer','storm','{"atk_pct":0.07}','{"crit_flat":0.05}','{"damage_pct":0.08,"proc_chance":0.14,"proc_damage_pct":0.25}',array['marksman']),
('wild_hunter','Wild Hunter','Cazador Salvaje','archer','wild','{"dodge_flat":0.04}','{"damage_pct":0.06,"def_pct":0.05}','{"crit_flat":0.04,"damage_reduction_pct":0.05}',array['hunter','scout']),
('night_reaper','Night Reaper','Segador Nocturno','assassin','shadow','{"crit_flat":0.05}','{"damage_pct":0.07}','{"proc_chance":0.18,"proc_damage_pct":0.28}',array['shadow','executioner']),
('venomfang','Venomfang','Colmillo Venenoso','assassin','venom','{"atk_pct":0.06}','{"skill_damage_pct":0.08,"dodge_flat":0.03}','{"damage_pct":0.08,"proc_chance":0.15,"proc_damage_pct":0.22}',array['venom']),
('riftwalker','Riftwalker','Caminante de la Grieta',null,'rift','{"atk_pct":0.04,"def_pct":0.04}','{"crit_flat":0.03,"dodge_flat":0.03}','{"damage_pct":0.06,"damage_reduction_pct":0.04}',array[]::text[]),
('wayfarer','Wayfarer','Caminante Errante',null,'adventure','{"def_pct":0.05}','{"atk_pct":0.05}','{"crit_flat":0.03,"dodge_flat":0.03}',array[]::text[])
on conflict(id) do update set name_en=excluded.name_en,name_es=excluded.name_es,class_key=excluded.class_key,theme=excluded.theme,bonus_2=excluded.bonus_2,bonus_4=excluded.bonus_4,bonus_6=excluded.bonus_6,recommended_specializations=excluded.recommended_specializations,active=true;

insert into public.phase3_specializations(id,class_key,name_en,name_es,description_en,description_es,stat_modifiers,passive_effects,pvp_modifiers,ai_priority,recommended_set_id) values
('guardian','warrior','Guardian','Guardián','Defensive frontline with mitigation and control.','Primera línea defensiva con mitigación y control.','{"def_pct":0.12}','{"damage_reduction_pct":0.06}','{"damage_reduction_pct":-0.02}','{"style":"defensive","guard_weight":1.45}','iron_bastion'),
('berserker','warrior','Berserker','Berserker','High pressure melee build that trades safety for damage.','Build cuerpo a cuerpo de alta presión que cambia seguridad por daño.','{"atk_pct":0.12,"crit_flat":0.03}','{"damage_pct":0.06,"incoming_damage_pct":0.04}','{"damage_pct":-0.03}','{"style":"aggressive","damage_weight":1.45}','ash_lord'),
('gladiator','warrior','Gladiator','Gladiador','Balanced duelist with reliable offense and defense.','Duelista equilibrado con ataque y defensa consistentes.','{"atk_pct":0.06,"def_pct":0.06,"crit_flat":0.02}','{"damage_pct":0.03}','{}','{"style":"balanced","execute_weight":1.15}','ash_lord'),
('pyromancer','mage','Pyromancer','Piromante','Burst caster focused on critical spell damage.','Mago explosivo centrado en daño crítico de hechizos.','{"atk_pct":0.06,"crit_flat":0.03}','{"skill_damage_pct":0.12}','{"skill_damage_pct":-0.03}','{"style":"aggressive","damage_weight":1.40}','ember_savant'),
('cryomancer','mage','Cryomancer','Criomante','Control caster with efficient mana and protection.','Mago de control con maná eficiente y protección.','{"def_pct":0.08}','{"mana_cost_pct":-0.12,"damage_reduction_pct":0.05}','{}','{"style":"defensive","guard_weight":1.25}','frost_weaver'),
('arcanist','mage','Arcanist','Arcanista','Flexible arcane specialist with consistent skill pressure.','Especialista arcano flexible con presión constante de habilidades.','{"atk_pct":0.07}','{"skill_damage_pct":0.08,"crit_flat":0.02}','{}','{"style":"smart","damage_weight":1.20}','ember_savant'),
('marksman','archer','Marksman','Tirador','Precision ranged build with strong critical pressure.','Build de precisión a distancia con fuerte presión crítica.','{"atk_pct":0.10,"crit_flat":0.04}','{"damage_pct":0.04}','{"crit_flat":-0.01}','{"style":"aggressive","damage_weight":1.30}','storm_marksman'),
('hunter','archer','Hunter','Cazador','Adaptive hunter with balanced damage and survivability.','Cazador adaptable con daño y supervivencia equilibrados.','{"atk_pct":0.06,"def_pct":0.04}','{"dodge_flat":0.03,"damage_pct":0.04}','{}','{"style":"smart","damage_weight":1.15}','wild_hunter'),
('scout','archer','Scout','Explorador','Mobile skirmisher built around evasion and safe pressure.','Hostigador móvil basado en evasión y presión segura.','{"dodge_flat":0.06,"def_pct":0.04}','{"damage_reduction_pct":0.03}','{"dodge_flat":-0.01}','{"style":"defensive","guard_weight":1.15}','wild_hunter'),
('venom','assassin','Venom','Veneno','Persistent damage specialist with efficient lethal windows.','Especialista en daño persistente con ventanas letales eficientes.','{"atk_pct":0.07}','{"skill_damage_pct":0.08,"proc_chance":0.10,"proc_damage_pct":0.16}','{"proc_damage_pct":-0.04}','{"style":"smart","damage_weight":1.20}','venomfang'),
('shadow','assassin','Shadow','Sombras','Evasive assassin with critical ambush pressure.','Asesino evasivo con presión crítica de emboscada.','{"dodge_flat":0.06,"crit_flat":0.03}','{"damage_pct":0.04}','{"dodge_flat":-0.01}','{"style":"smart","damage_weight":1.25}','night_reaper'),
('executioner','assassin','Executioner','Ejecutor','Finisher specialized in low-health targets.','Rematador especializado en objetivos con poca vida.','{"atk_pct":0.09,"crit_flat":0.02}','{"execute_bonus_pct":0.18}','{"execute_bonus_pct":-0.05}','{"style":"aggressive","execute_weight":1.55}','night_reaper')
on conflict(id) do update set class_key=excluded.class_key,name_en=excluded.name_en,name_es=excluded.name_es,description_en=excluded.description_en,description_es=excluded.description_es,stat_modifiers=excluded.stat_modifiers,passive_effects=excluded.passive_effects,pvp_modifiers=excluded.pvp_modifiers,ai_priority=excluded.ai_priority,recommended_set_id=excluded.recommended_set_id,active=true;

insert into public.phase3_specialization_skills(id,specialization_id,name,name_es,kind,mana_cost,multiplier,cooldown_turns,damage_reduction,execute_threshold,armor_pierce,crit_bonus,min_level,metadata) values
('guardian_shield_wall','guardian','Shield Wall','Muro de Escudos','guard',10,0.85,3,0.48,0,0,0,10,'{"role":"mitigation"}'),
('guardian_counter','guardian','Aegis Counter','Contraataque del Égida','damage',12,1.28,3,1,0,0.12,0,12,'{"role":"counter"}'),
('berserker_bloodrage','berserker','Bloodrage','Furia de Sangre','damage',12,1.58,3,1,0,0,0.05,10,'{"role":"burst"}'),
('berserker_reckless_finish','berserker','Reckless Finish','Final Temerario','execute',16,1.82,4,1,0.30,0.08,0.03,12,'{"role":"execute"}'),
('gladiator_riposte','gladiator','Riposte','Riposte','damage',10,1.38,2,1,0,0.16,0.02,10,'{"role":"duel"}'),
('gladiator_iron_tempo','gladiator','Iron Tempo','Tempo de Hierro','guard',9,0.92,3,0.62,0,0,0,12,'{"role":"tempo"}'),
('pyro_firelance','pyromancer','Fire Lance','Lanza de Fuego','damage',16,1.64,3,1,0,0.08,0.04,10,'{"element":"fire"}'),
('pyro_inferno','pyromancer','Inferno Pulse','Pulso Infernal','damage',24,1.92,5,1,0,0.05,0.03,14,'{"element":"fire","role":"burst"}'),
('cryo_icebarrier','cryomancer','Ice Barrier','Barrera de Hielo','guard',12,0.88,3,0.52,0,0,0,10,'{"element":"ice"}'),
('cryo_shatter','cryomancer','Shatter','Quebrar','damage',15,1.48,3,1,0,0.18,0.02,12,'{"element":"ice"}'),
('arcane_bolt','arcanist','Arcane Bolt','Proyectil Arcano','damage',10,1.36,2,1,0,0.12,0.02,10,'{"element":"arcane"}'),
('arcane_overload','arcanist','Arcane Overload','Sobrecarga Arcana','damage',20,1.74,4,1,0,0.10,0.03,14,'{"element":"arcane"}'),
('marksman_deadeye','marksman','Deadeye Shot','Disparo Certero','damage',11,1.52,3,1,0,0.14,0.06,10,'{"role":"precision"}'),
('marksman_finisher','marksman','Piercing Finish','Remate Perforante','execute',15,1.72,4,1,0.28,0.22,0.03,12,'{"role":"execute"}'),
('hunter_predator','hunter','Predator Strike','Golpe del Depredador','damage',11,1.42,2,1,0,0.10,0.03,10,'{"role":"hunt"}'),
('hunter_survival','hunter','Survival Stance','Postura de Supervivencia','guard',10,0.90,3,0.60,0,0,0,12,'{"role":"survival"}'),
('scout_skirmish','scout','Skirmish Shot','Disparo de Hostigamiento','damage',9,1.32,2,1,0,0.08,0.03,10,'{"role":"mobility"}'),
('scout_evasive','scout','Evasive Volley','Volea Evasiva','guard',11,0.94,3,0.66,0,0,0,12,'{"role":"evasion"}'),
('venom_toxic_cut','venom','Toxic Cut','Corte Tóxico','damage',10,1.38,2,1,0,0.08,0.03,10,'{"element":"poison","dot_hint":true}'),
('venom_black_bile','venom','Black Bile','Bilis Negra','damage',15,1.62,4,1,0,0.10,0.02,13,'{"element":"poison","dot_hint":true}'),
('shadow_ambush','shadow','Shadow Ambush','Emboscada Sombría','damage',12,1.52,3,1,0,0.12,0.06,10,'{"role":"ambush"}'),
('shadow_veil','shadow','Veil Step','Paso del Velo','guard',10,0.90,3,0.64,0,0,0,12,'{"role":"evasion"}'),
('executioner_cull','executioner','Cull','Sacrificio','execute',12,1.72,3,1,0.35,0.12,0.03,10,'{"role":"execute"}'),
('executioner_final_word','executioner','Final Word','Última Palabra','execute',18,2.00,5,1,0.25,0.18,0.04,14,'{"role":"execute"}')
on conflict(id) do update set specialization_id=excluded.specialization_id,name=excluded.name,name_es=excluded.name_es,kind=excluded.kind,mana_cost=excluded.mana_cost,multiplier=excluded.multiplier,cooldown_turns=excluded.cooldown_turns,damage_reduction=excluded.damage_reduction,execute_threshold=excluded.execute_threshold,armor_pierce=excluded.armor_pierce,crit_bonus=excluded.crit_bonus,min_level=excluded.min_level,metadata=excluded.metadata;

create or replace function public.phase3_effect_add(p_base jsonb,p_add jsonb)
returns jsonb language plpgsql immutable as $$
declare result jsonb:=coalesce(p_base,'{}'::jsonb); k text; v jsonb; current_num numeric; add_num numeric;
begin
  if p_add is null then return result; end if;
  for k,v in select key,value from jsonb_each(p_add) loop
    if jsonb_typeof(v)='number' then
      current_num:=coalesce((result->>k)::numeric,0); add_num:=(v#>>'{}')::numeric;
      result:=jsonb_set(result,array[k],to_jsonb(current_num+add_num),true);
    else result:=jsonb_set(result,array[k],v,true); end if;
  end loop;
  return result;
end $$;

create or replace function public.phase3_build_profile(p_character uuid,p_pvp boolean default false)
returns jsonb language plpgsql security definer set search_path=public as $$
declare c public.characters%rowtype; eq public.equipment%rowtype; spec public.phase3_specializations%rowtype; s public.phase3_set_definitions%rowtype; ids uuid[]; pieces integer; effects jsonb:='{}'::jsonb; sets_json jsonb:='[]'::jsonb; e2 boolean; e4 boolean; e6 boolean;
begin
  select * into c from public.characters where id=p_character; if not found then raise exception 'character_not_found'; end if;
  select * into eq from public.equipment where character_id=p_character;
  ids:=array[eq.weapon_item_id,eq.helmet_item_id,eq.armor_item_id,eq.gloves_item_id,eq.boots_item_id,eq.ring_item_id];
  if c.specialization is not null then
    select * into spec from public.phase3_specializations where id=c.specialization and class_key=c.class and active=true;
    if found then effects:=public.phase3_effect_add(effects,spec.stat_modifiers);effects:=public.phase3_effect_add(effects,spec.passive_effects);if p_pvp then effects:=public.phase3_effect_add(effects,spec.pvp_modifiers); end if; end if;
  end if;
  for s in select * from public.phase3_set_definitions where active=true order by id loop
    select count(*) into pieces from public.item_instances i where i.id=any(ids) and i.set_id=s.id;
    if pieces>0 then
      e2:=pieces>=2;e4:=pieces>=4;e6:=pieces>=6;
      if e2 then effects:=public.phase3_effect_add(effects,s.bonus_2); end if;
      if e4 then effects:=public.phase3_effect_add(effects,s.bonus_4); end if;
      if e6 then effects:=public.phase3_effect_add(effects,s.bonus_6); end if;
      sets_json:=sets_json||jsonb_build_array(jsonb_build_object('id',s.id,'name',s.name_en,'nameEs',s.name_es,'pieces',pieces,'classKey',s.class_key,'bonus2',s.bonus_2,'bonus4',s.bonus_4,'bonus6',s.bonus_6,'active2',e2,'active4',e4,'active6',e6));
    end if;
  end loop;
  effects:=jsonb_set(effects,'{atk_pct}',to_jsonb(least(0.35,greatest(-0.20,coalesce((effects->>'atk_pct')::numeric,0)))),true);
  effects:=jsonb_set(effects,'{def_pct}',to_jsonb(least(0.40,greatest(-0.20,coalesce((effects->>'def_pct')::numeric,0)))),true);
  effects:=jsonb_set(effects,'{crit_flat}',to_jsonb(least(0.25,greatest(-0.20,coalesce((effects->>'crit_flat')::numeric,0)))),true);
  effects:=jsonb_set(effects,'{dodge_flat}',to_jsonb(least(0.18,greatest(-0.15,coalesce((effects->>'dodge_flat')::numeric,0)))),true);
  effects:=jsonb_set(effects,'{damage_pct}',to_jsonb(least(0.30,greatest(-0.20,coalesce((effects->>'damage_pct')::numeric,0)))),true);
  effects:=jsonb_set(effects,'{damage_reduction_pct}',to_jsonb(least(0.25,greatest(-0.10,coalesce((effects->>'damage_reduction_pct')::numeric,0)))),true);
  effects:=jsonb_set(effects,'{skill_damage_pct}',to_jsonb(least(0.30,greatest(-0.20,coalesce((effects->>'skill_damage_pct')::numeric,0)))),true);
  effects:=jsonb_set(effects,'{mana_cost_pct}',to_jsonb(least(0.10,greatest(-0.25,coalesce((effects->>'mana_cost_pct')::numeric,0)))),true);
  effects:=jsonb_set(effects,'{proc_chance}',to_jsonb(least(0.25,greatest(0,coalesce((effects->>'proc_chance')::numeric,0)))),true);
  effects:=jsonb_set(effects,'{proc_damage_pct}',to_jsonb(least(0.40,greatest(0,coalesce((effects->>'proc_damage_pct')::numeric,0)))),true);
  effects:=jsonb_set(effects,'{execute_bonus_pct}',to_jsonb(least(0.25,greatest(0,coalesce((effects->>'execute_bonus_pct')::numeric,0)))),true);
  effects:=jsonb_set(effects,'{incoming_damage_pct}',to_jsonb(least(0.10,greatest(-0.10,coalesce((effects->>'incoming_damage_pct')::numeric,0)))),true);
  return jsonb_build_object('specialization',case when spec.id is null then null else jsonb_build_object('id',spec.id,'name',spec.name_en,'nameEs',spec.name_es,'description',spec.description_en,'descriptionEs',spec.description_es,'aiPriority',spec.ai_priority,'recommendedSetId',spec.recommended_set_id) end,'sets',sets_json,'effects',effects,'caps',jsonb_build_object('crit',case when p_pvp then 0.65 else 0.75 end,'dodge',case when p_pvp then 0.50 else 0.60 end),'pvp',p_pvp);
end $$;

create or replace function public.phase3_set_specialization(p_character uuid,p_specialization text)
returns jsonb language plpgsql security definer set search_path=public as $$
declare c public.characters%rowtype; s public.phase3_specializations%rowtype; gold_cost integer:=0; essence_cost integer:=0; essence bigint:=0;
begin
  select * into c from public.characters where id=p_character for update; if not found then raise exception 'character_not_found'; end if;
  select * into s from public.phase3_specializations where id=p_specialization and active=true; if not found or s.class_key<>c.class then raise exception 'specialization_not_available'; end if;
  if c.level<s.unlock_level then raise exception 'specialization_level_required'; end if;
  if c.specialization=p_specialization then return jsonb_build_object('changed',false,'specialization',p_specialization,'goldCost',0,'essenceCost',0); end if;
  if c.specialization is not null then
    gold_cost:=least(2000,400+c.specialization_respec_count*200);essence_cost:=least(10,3+c.specialization_respec_count);
    if c.gold<gold_cost then raise exception 'not_enough_gold_for_respec'; end if;
    select coalesce(amount,0) into essence from public.resources where character_id=p_character and resource_key='essence' for update;
    if essence<essence_cost then raise exception 'not_enough_essence_for_respec'; end if;
    update public.characters set gold=gold-gold_cost,specialization=p_specialization,specialization_respec_count=specialization_respec_count+1,updated_at=now() where id=p_character;
    update public.resources set amount=amount-essence_cost where character_id=p_character and resource_key='essence';
  else update public.characters set specialization=p_specialization,updated_at=now() where id=p_character; end if;
  insert into public.game_transactions(character_id,kind,delta) values(p_character,'specialization_change',jsonb_build_object('specialization',p_specialization,'gold',-gold_cost,'essence',-essence_cost));
  return jsonb_build_object('changed',true,'specialization',p_specialization,'goldCost',gold_cost,'essenceCost',essence_cost,'respecCount',case when c.specialization is null then c.specialization_respec_count else c.specialization_respec_count+1 end);
end $$;

create or replace function public.phase3_equip_item(p_character uuid,p_item uuid)
returns jsonb language plpgsql security definer set search_path=public as $$
declare c public.characters%rowtype; i public.item_instances%rowtype; slot text; set_class text; col text;
begin
  select * into c from public.characters where id=p_character; if not found then raise exception 'character_not_found'; end if;
  select * into i from public.item_instances where id=p_item and owner_character_id=p_character; if not found then raise exception 'item_not_found'; end if;
  slot:=coalesce(i.metadata->>'slot',(select d.slot from public.item_definitions d where d.id=i.definition_id));
  if slot not in ('weapon','helmet','armor','gloves','boots','ring') then raise exception 'item_cannot_be_equipped'; end if;
  if i.set_id is not null then select class_key into set_class from public.phase3_set_definitions where id=i.set_id;if set_class is not null and set_class<>c.class then raise exception 'set_class_mismatch'; end if;end if;
  insert into public.equipment(character_id) values(p_character) on conflict(character_id) do nothing;
  col:=slot||'_item_id';execute format('update public.equipment set %I=$1, updated_at=now() where character_id=$2',col) using p_item,p_character;
  return jsonb_build_object('equipped',true,'slot',slot,'itemId',p_item,'build',public.phase3_build_profile(p_character,false));
end $$;

create or replace function public.phase3_unequip_slot(p_character uuid,p_slot text)
returns jsonb language plpgsql security definer set search_path=public as $$
declare col text;
begin
  if p_slot not in ('weapon','helmet','armor','gloves','boots','ring') then raise exception 'invalid_slot'; end if;
  col:=p_slot||'_item_id';execute format('update public.equipment set %I=null, updated_at=now() where character_id=$1',col) using p_character;
  return jsonb_build_object('unequipped',true,'slot',p_slot,'build',public.phase3_build_profile(p_character,false));
end $$;

create or replace function public.phase3_award_set_drop(p_character uuid,p_source text,p_level integer,p_force boolean default false)
returns jsonb language plpgsql security definer set search_path=public as $$
declare c public.characters%rowtype; s public.phase3_set_definitions%rowtype; slots text[]:=array['weapon','helmet','armor','gloves','boots','ring']; slot text; chance numeric; base integer; atk integer:=0; def integer:=0; rarity text; new_item uuid; item_name text;
begin
  select * into c from public.characters where id=p_character; if not found then raise exception 'character_not_found'; end if;
  chance:=case p_source when 'rift' then 0.55 when 'boss' then 0.32 when 'expedition' then 0.18 else 0.08 end;
  if not p_force and random()>chance then return jsonb_build_object('awarded',false); end if;
  select * into s from public.phase3_set_definitions where active=true and (class_key is null or class_key=c.class) order by random() limit 1;
  if not found then return jsonb_build_object('awarded',false); end if;
  slot:=slots[1+floor(random()*array_length(slots,1))::integer];base:=greatest(4,4+p_level*2);
  atk:=case slot when 'weapon' then base when 'ring' then ceil(base*.55)::integer when 'gloves' then ceil(base*.40)::integer else ceil(base*.20)::integer end;
  def:=case slot when 'armor' then base when 'helmet' then ceil(base*.75)::integer when 'boots' then ceil(base*.60)::integer when 'gloves' then ceil(base*.45)::integer when 'ring' then ceil(base*.20)::integer else 0 end;
  rarity:=case when p_source='rift' and p_level>=12 then 'EPIC' when p_level>=8 then 'RARE' else 'UNCOMMON' end;
  item_name:=s.name_en||' '||initcap(slot);
  insert into public.item_instances(owner_character_id,definition_id,custom_name,rarity,atk,def,enhancement_level,set_id,metadata)
  values(p_character,null,item_name,rarity,atk,def,0,s.id,jsonb_build_object('type','gear','slot',slot,'set_id',s.id,'source',p_source,'value',greatest(20,atk*5+def*4))) returning id into new_item;
  return jsonb_build_object('awarded',true,'itemId',new_item,'name',item_name,'setId',s.id,'setName',s.name_en,'setNameEs',s.name_es,'slot',slot,'rarity',rarity,'atk',atk,'def',def);
end $$;

alter table public.phase3_set_definitions enable row level security;
alter table public.phase3_specializations enable row level security;
alter table public.phase3_specialization_skills enable row level security;

revoke all on function public.phase3_build_profile(uuid,boolean) from anon,authenticated;
revoke all on function public.phase3_set_specialization(uuid,text) from anon,authenticated;
revoke all on function public.phase3_equip_item(uuid,uuid) from anon,authenticated;
revoke all on function public.phase3_unequip_slot(uuid,text) from anon,authenticated;
revoke all on function public.phase3_award_set_drop(uuid,text,integer,boolean) from anon,authenticated;
grant execute on function public.phase3_build_profile(uuid,boolean) to service_role;
grant execute on function public.phase3_set_specialization(uuid,text) to service_role;
grant execute on function public.phase3_equip_item(uuid,uuid) to service_role;
grant execute on function public.phase3_unequip_slot(uuid,text) to service_role;
grant execute on function public.phase3_award_set_drop(uuid,text,integer,boolean) to service_role;
