import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {PET_RARITIES,PHASE5_TABS,RANKING_KEYS,CODEX_CATEGORIES,plainText,petLevelFromXp,petEvolutionRequirement,isOnline,eventState} from '../frontend/phase5-core.js';

const schema=fs.readFileSync(new URL('../database/migrations/20260906_phase5_living_world_schema.sql',import.meta.url),'utf8');
const runtime=fs.readFileSync(new URL('../database/migrations/20260906_phase5_living_world_runtime.sql',import.meta.url),'utf8');
const integrations=fs.readFileSync(new URL('../database/migrations/20260906_phase5_living_world_integrations.sql',import.meta.url),'utf8');
const edge=fs.readFileSync(new URL('../supabase/functions/phase5-engine/index.ts',import.meta.url),'utf8');
const ui=fs.readFileSync(new URL('../frontend/phase5.js',import.meta.url),'utf8');
const css=fs.readFileSync(new URL('../frontend/phase5.css',import.meta.url),'utf8');
const index=fs.readFileSync(new URL('../frontend/index.html',import.meta.url),'utf8');

const allSql=`${schema}\n${runtime}\n${integrations}`;

test('Phase 5 defines the five launch pets and complete rarity ladder',()=>{
  for(const pet of ['Lobo de Ceniza','Zorro Astral','Halcón de Grieta','Espíritu Antiguo','Dracónido'])assert.match(schema,new RegExp(pet));
  assert.deepEqual(PET_RARITIES,['common','uncommon','rare','epic','legendary','mythic']);
  assert.match(schema,/passive_percent[^;]+<=0\.02/s);
});

test('pet obtain, equip, XP leveling and evolution are server-authoritative',()=>{
  assert.match(runtime,/phase5_try_pet_drop/);assert.match(runtime,/phase5_pet_equip/);assert.match(runtime,/phase5_pet_add_xp/);assert.match(runtime,/phase5_pet_evolve/);
  assert.match(runtime,/Evolution item required/);assert.match(schema,/pet_evolution_core/);assert.match(integrations,/trg_phase5_rift_pet/);assert.match(integrations,/trg_phase5_world_boss_pet/);assert.match(integrations,/trg_phase5_clan_boss_pet/);
  assert.equal(petLevelFromXp(0),1);assert.equal(petLevelFromXp(900),4);assert.deepEqual(petEvolutionRequirement({evolution_level:20,evolution_resource_key:'essence',evolution_resource_amount:80,evolution_item_id:'pet_evolution_core'},1),{level:30,resource:'essence',amount:160,item:'pet_evolution_core'});
});

test('pet bonuses stay small and integrate gathering crafting XP and boss damage',()=>{
  assert.match(integrations,/phase5_transaction_bonus_hook/);assert.match(integrations,/phase5_crafting_bonus_hook/);assert.match(integrations,/phase5_pet_bonus\(p_character_id,'boss_damage'\)/);assert.match(integrations,/phase5_event_bonus\('boss_damage'\)/);
  assert.match(schema,/0\.02/);
});

test('social supports friends, requests, safe profiles and basic online state',()=>{
  for(const name of ['friend_requests','friendships','player_presence'])assert.match(schema,new RegExp(`create table if not exists public\\.${name}`));
  assert.match(runtime,/phase5_friend_request/);assert.match(runtime,/phase5_friend_respond/);assert.match(edge,/safeInspect/);assert.doesNotMatch(edge,/select\([^)]*email/i);assert.doesNotMatch(edge,/wallet/);
  assert.equal(isOnline(new Date(Date.now()-60_000).toISOString()),true);assert.equal(isOnline(new Date(Date.now()-10*60_000).toISOString()),false);
});

test('chat is plain text with spam rate limit, mute, report and no arbitrary HTML',()=>{
  assert.equal(plainText('<b>hola</b>\n mundo'),'bhola/b mundo');
  assert.match(runtime,/phase5_chat_send/);assert.match(runtime,/phase5_rate_gate\(p_character,'chat_send',5,10\)/);assert.match(runtime,/Duplicate message/);assert.match(runtime,/phase5_chat_mute/);assert.match(runtime,/phase5_chat_report/);
  assert.match(runtime,/\[<>/);assert.match(ui,/esc\(m\.body\)/);
});

test('rankings cover all requested categories',()=>{
  assert.deepEqual(RANKING_KEYS,['level','power','arena','world_boss','clans','professions','collection','season']);
  for(const key of RANKING_KEYS)assert.match(runtime,new RegExp(`'${key}'`));
  assert.match(runtime,/phase5_refresh_rankings_if_needed/);
});

test('weekly live events and temporary monthly templates are data-driven',()=>{
  for(const day of ['clan_boss_monday','gathering_tuesday','arena_wednesday','rift_thursday','world_event_friday','clan_wars_saturday','world_boss_sunday'])assert.match(schema,new RegExp(day));
  for(const t of ['halloween','winter','anniversary','rift_season'])assert.match(schema,new RegExp(`'${t}'`));
  assert.match(runtime,/phase5_refresh_events/);assert.match(runtime,/phase5_schedule_template/);assert.equal(eventState({starts_at:new Date(Date.now()-1000).toISOString(),ends_at:new Date(Date.now()+1000).toISOString()}),'active');
});

test('event rewards and claims are duplicate protected',()=>{
  assert.match(schema,/primary key\(event_instance_id,character_id\)/);assert.match(runtime,/phase5_claim_event/);assert.match(runtime,/Event reward already claimed/);assert.match(schema,/phase5_action_receipts/);
});

test('achievements and titles include all requested examples and selected title UI',()=>{
  for(const x of ['Matadragones','Maestro Herrero','Inmortal','Señor de la Grieta','Campeón de Arena'])assert.match(schema,new RegExp(x));
  assert.match(runtime,/phase5_sync_titles/);assert.match(runtime,/phase5_set_title/);assert.match(ui,/phase5-title-badge/);assert.match(ui,/data-p5-title/);
});

test('expanded Codex has all requested categories and pets integrated',()=>{
  assert.deepEqual(CODEX_CATEGORIES,['monsters','bosses','equipment','sets','pets','resources','zones']);
  assert.match(runtime,/phase5_sync_codex/);assert.match(schema,/select 'pets',pet_key/);
});

test('anti-abuse and privacy controls are enforced in DB and Edge',()=>{
  assert.match(allSql,/enable row level security/g);assert.match(allSql,/revoke all on/g);assert.match(runtime,/phase5_rate_gate/g);assert.match(schema,/unique\(reporter_character_id,message_id\)/);assert.match(schema,/receipt_key text primary key/);
  assert.doesNotMatch(edge,/auth\.users/);assert.doesNotMatch(ui,/innerHTML\s*=.*m\.body/);
});

test('mobile UI stays in More with sheets and tabs instead of new bottom navigation',()=>{
  assert.deepEqual(PHASE5_TABS,['pets','social','rankings','events','achievements','codex']);assert.match(ui,/isMore\(\)/);assert.match(ui,/phase5-overlay/);assert.match(css,/@media\(max-width:620px\)/);assert.match(css,/overflow-x:auto/);assert.match(index,/phase5\.css/);assert.match(index,/phase5\.js/);assert.doesNotMatch(ui,/MutationObserver/);
});

test('Phase 5 UI exposes required actions',()=>{
  for(const action of ['petEquip','petEvolve','friendRequest','friendRespond','friendRemove','chatSend','chatMute','chatReport','eventClaim','titleSet','notificationRead'])assert.match(ui,new RegExp(action));
  assert.match(edge,/op==='search'/);assert.match(edge,/op==='inspect'/);
});
