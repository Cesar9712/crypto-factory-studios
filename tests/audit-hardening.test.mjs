import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const read=p=>readFile(new URL(`../${p}`,import.meta.url),'utf8');
const securityMigration=await read('database/migrations/20260906_full_game_security_concurrency_hardening.sql');
const leaseFix=await read('database/migrations/20260906_full_game_action_lease_false_fix.sql');
const rlsGrantFix=await read('database/migrations/20260906_full_game_rls_server_only_grants.sql');
const indexMigration=await read('database/migrations/20260906_full_game_fk_performance_indexes.sql');
const combat=await read('supabase/functions/combat-engine/index.ts');
const manual=await read('supabase/functions/manual-combat/index.ts');
const server=await read('backend/server.mjs');
const fast=await read('frontend/phase1-auto-fast.js');
const hotfix=await read('frontend/runtime-hotfix.js');

test('P0 Phase3 privileged mutation RPCs are removed from client roles',()=>{
  for(const fn of ['phase3_award_set_drop','phase3_equip_item','phase3_unequip_slot','phase3_set_specialization','phase4_bastion_craft_benefit']) assert.match(securityMigration,new RegExp(`revoke\\s+all\\s+on\\s+function\\s+public\\.${fn}`,'i'),fn);
  assert.match(securityMigration,/from public,anon,authenticated/i);
});

test('atomic gameplay primitives are service-role only and lock authoritative rows',()=>{
  for(const fn of ['fullgame_acquire_action_lease','fullgame_release_action_lease','fullgame_regen_character','fullgame_consume_energy','fullgame_apply_character_progress','fullgame_allocate_stat']) assert.match(securityMigration,new RegExp(`create\\s+or\\s+replace\\s+function\\s+public\\.${fn}`,'i'));
  assert.match(securityMigration,/revoke all on function public\.fullgame_acquire_action_lease[\s\S]*from public,anon,authenticated/i);
  assert.match(securityMigration,/grant execute on function public\.fullgame_acquire_action_lease[\s\S]*to service_role/i);
  assert.match(securityMigration,/for update/i);
  assert.match(securityMigration,/primary key\(character_id,action_key\)/i);
});

test('contested action lease returns explicit false rather than NULL',()=>{
  assert.match(leaseFix,/return coalesce\(v_acquired=v_request,false\)/i);
  assert.match(leaseFix,/revoke all on function public\.fullgame_acquire_action_lease/i);
});

test('RLS tables with no policies are explicitly server-only at table grant level',()=>{
  assert.match(rlsGrantFix,/c\.relrowsecurity/i);
  assert.match(rlsGrantFix,/not exists[\s\S]*pg_policy/i);
  assert.match(rlsGrantFix,/revoke all privileges on table/i);
  assert.match(rlsGrantFix,/public, anon, authenticated/i);
  assert.match(rlsGrantFix,/service_role/i);
});

test('automatic combat uses atomic regeneration, energy, rewards, stats and a one-shot lease',()=>{
  for(const fn of ['fullgame_regen_character','fullgame_consume_energy','fullgame_apply_character_progress','fullgame_allocate_stat','fullgame_acquire_action_lease','fullgame_release_action_lease']) assert.match(combat,new RegExp(`admin\\.rpc\\('${fn}'`));
  assert.doesNotMatch(combat,/update\(\{energy:Number\(c\.energy\)-amount\}\)/);
});

test('manual combat reward path uses atomic progression and regeneration',()=>{
  assert.match(manual,/admin\.rpc\('fullgame_apply_character_progress'/);
  assert.match(manual,/admin\.rpc\('fullgame_regen_character'/);
});

test('production fails closed instead of serving local demo economy',()=>{
  assert.match(server,/PRODUCTION_RUNTIME/);
  assert.match(server,/503/);
  assert.match(server,/Game backend is not configured/i);
});

test('fast combat never fabricates victory after result timeout',()=>{
  assert.match(fast,/SIN CONFIRMAR|UNCONFIRMED/);
  assert.match(fast,/confirmed/);
  assert.doesNotMatch(fast,/victory=!\/Bastión\|Bastion\/i/);
});

test('optimistic travel is reconciled against authoritative server state',()=>{
  assert.match(hotfix,/authoritative/i);
  assert.match(hotfix,/reconcile/i);
  assert.match(hotfix,/\/api\/state/);
});

test('FK performance migration is additive and non-destructive',()=>{
  assert.match(indexMigration,/create index if not exists/i);
  assert.doesNotMatch(indexMigration,/drop\s+table|truncate|delete\s+from/i);
});
