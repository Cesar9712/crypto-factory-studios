import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const schema=fs.readFileSync(new URL('../database/migrations/20260906_phase5_living_world_schema.sql',import.meta.url),'utf8');
const runtime=fs.readFileSync(new URL('../database/migrations/20260906_phase5_living_world_runtime.sql',import.meta.url),'utf8');
const integrations=fs.readFileSync(new URL('../database/migrations/20260906_phase5_living_world_integrations.sql',import.meta.url),'utf8');
const audit=fs.readFileSync(new URL('../database/migrations/20260906_phase5_audit_hardening.sql',import.meta.url),'utf8');
const followup=fs.readFileSync(new URL('../database/migrations/20260906_phase5_audit_followup.sql',import.meta.url),'utf8');
const edge=fs.readFileSync(new URL('../supabase/functions/phase5-engine/index.ts',import.meta.url),'utf8');
const ui=fs.readFileSync(new URL('../frontend/phase5.js',import.meta.url),'utf8');
const css=fs.readFileSync(new URL('../frontend/phase5.css',import.meta.url),'utf8');
const all=`${schema}\n${runtime}\n${integrations}\n${audit}\n${followup}`;

test('01 pets: five launch pets, complete rarity ladder, small bonuses, XP/evolution and all obtain sources',()=>{
  for(const p of ['Lobo de Ceniza','Zorro Astral','Halcón de Grieta','Espíritu Antiguo','Dracónido'])assert.match(schema,new RegExp(p));
  for(const r of ['common','uncommon','rare','epic','legendary','mythic'])assert.match(schema,new RegExp(`'${r}'`));
  assert.match(schema,/passive_percent[^;]+<=0\.02/s);
  for(const fn of ['phase5_pet_equip','phase5_pet_add_xp','phase5_pet_evolve','phase5_try_pet_drop'])assert.match(runtime,new RegExp(fn));
  for(const src of ["'rift'","'quest'","'world_boss'","'clan_boss'","'collection'","'event'"])assert.match(runtime,new RegExp(src));
});

test('02 codex: all seven categories exist, real zones sync and null dynamic item IDs cannot abort state',()=>{
  for(const cat of ['monsters','bosses','equipment','sets','pets','resources','zones'])assert.match(schema,new RegExp(`'${cat}'`));
  assert.match(audit,/select 'zones',id,name,name,'🗺️','Mundo' from public\.zones/);
  assert.match(followup,/definition_id is not null/);
  assert.match(followup,/m\.enemy_id is not null/);
  assert.match(followup,/values\('zones',v_zone/);
});

test('03 social: requests, friends, profiles/presence and remove are rate protected',()=>{
  assert.match(schema,/create table if not exists public\.friend_requests/);
  assert.match(schema,/create table if not exists public\.friendships/);
  assert.match(schema,/create table if not exists public\.player_presence/);
  assert.match(runtime,/phase5_rate_gate\(p_character,'friend_request',8,60\)/);
  assert.match(audit,/phase5_rate_gate\(p_character,'friend_remove',12,60\)/);
  assert.match(audit,/phase5_rate_gate\(p_character,'state_refresh',30,60\)/);
});

test('04 chat: plain text, spam/duplicate limits, mute and report remain server authoritative',()=>{
  assert.match(runtime,/phase5_rate_gate\(p_character,'chat_send',5,10\)/);
  assert.match(runtime,/Duplicate message/);
  assert.match(runtime,/regexp_replace\(coalesce\(p_body/);
  assert.match(runtime,/phase5_chat_mute/);
  assert.match(runtime,/phase5_chat_report/);
  assert.match(ui,/esc\(m\.body\)/);
});

test('05 rankings and privacy: all eight boards exist and Edge does not expose email/wallet',()=>{
  for(const k of ['level','power','arena','world_boss','clans','professions','collection','season'])assert.match(runtime,new RegExp(`'${k}'`));
  assert.doesNotMatch(edge,/select\([^)]*email/i);
  assert.doesNotMatch(edge,/wallet/i);
  assert.match(edge,/id,name,class,level,renown/);
});

test('06 achievements/titles: five requested titles track progress before unlock and equip remains gated',()=>{
  for(const t of ['Matadragones','Maestro Herrero','Inmortal','Señor de la Grieta','Campeón de Arena'])assert.match(schema,new RegExp(t));
  assert.match(audit,/case when v_boss>=5000 then now\(\) else null end/);
  assert.match(audit,/case when v_level>=25 then now\(\) else null end/);
  assert.match(runtime,/Title not unlocked/);
  assert.match(ui,/phase5-title-badge/);
});

test('07 live events: weekly plus all temporary templates support real bonus, eligibility, reward and claim without hardcoded calendar dates',()=>{
  for(const e of ['clan_boss_monday','gathering_tuesday','arena_wednesday','rift_thursday','world_event_friday','clan_wars_saturday','world_boss_sunday'])assert.match(schema,new RegExp(e));
  for(const t of ['halloween','winter','anniversary','rift_season'])assert.match(audit,new RegExp(`when '${t}'`));
  assert.match(audit,/event_type/);
  assert.match(audit,/bonus_percent/);
  assert.match(audit,/coalesce\(d\.event_type,i\.config->>'event_type'\)/);
  assert.match(audit,/phase5_event_eligible\(p_character,v_type,v_start,v_end\)/);
  assert.match(audit,/phase5_action_receipts[\s\S]+eventclaim:/);
});

test('08 notifications: event, boss, reward and ranking notices are deduped and corrected in place',()=>{
  assert.match(audit,/Boss activo/);
  assert.match(audit,/Evento iniciado/);
  assert.match(audit,/Recompensa disponible/);
  assert.match(audit,/Ranking actualizado/);
  assert.match(schema,/unique\(character_id,dedupe_key\)/);
  assert.match(followup,/on conflict\(character_id,dedupe_key\) do update/);
});

test('09 antiabuse: rate gates serialize concurrent calls, cleanup old rows and replay receipts stay enforced',()=>{
  assert.match(audit,/pg_advisory_xact_lock\(hashtextextended/);
  assert.match(audit,/delete from public\.phase5_rate_events/);
  assert.match(schema,/receipt_key text primary key/);
  assert.match(schema,/primary key\(event_instance_id,character_id\)/);
  assert.match(all,/enable row level security/);
  assert.match(all,/revoke all on function/);
});

test('10 mobile/release: Phase 5 stays under More with sheet/tabs and mobile CSS; no extra observer/nav regression',()=>{
  assert.match(ui,/isMore\(\)/);
  assert.match(ui,/phase5-overlay/);
  assert.match(ui,/data-p5-tab/);
  assert.match(css,/@media\(max-width:620px\)/);
  assert.match(css,/overflow-x:auto/);
  assert.doesNotMatch(ui,/MutationObserver/);
});
