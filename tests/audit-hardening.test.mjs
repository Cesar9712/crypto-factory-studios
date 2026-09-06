import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const read=p=>readFile(new URL(`../${p}`,import.meta.url),'utf8');

const securityMigration=await read('database/migrations/20260906_full_game_audit_security_concurrency.sql');
const indexMigration=await read('database/migrations/20260906_full_game_audit_fk_indexes.sql');
const combat=await read('supabase/functions/combat-engine/index.ts');
const manual=await read('supabase/functions/manual-combat/index.ts');
const server=await read('backend/server.mjs');
const fast=await read('frontend/phase1-auto-fast.js');
const hotfix=await read('frontend/runtime-hotfix.js');

test('P0 Phase3 mutating SECURITY DEFINER RPCs are revoked from client roles',()=>{
  for(const fn of ['phase3_award_set_drop','phase3_equip_item','phase3_unequip_slot','phase3_choose_specialization','phase3_respec_specialization','phase4_bastion_craft_benefit']){
    assert.match(securityMigration,new RegExp(`revoke\\s+execute\\s+on\\s+function\\s+public\\.${fn}`,'i'),fn);
  }
  assert.match(securityMigration,/from public, anon, authenticated/i);
});

test('atomic gameplay primitives are server-only and row-lock authoritative',()=>{
  for(const fn of ['audit_regen_character','audit_spend_energy','audit_apply_progression','audit_allocate_stat','audit_acquire_action_lease']){
    assert.match(securityMigration,new RegExp(`create\\s+or\\s+replace\\s+function\\s+public\\.${fn}`,'i'));
    assert.match(securityMigration,new RegExp(`revoke\\s+execute\\s+on\\s+function\\s+public\\.${fn}`,'i'));
  }
  assert.match(securityMigration,/for update/i);
  assert.match(securityMigration,/pg_advisory_xact_lock/i);
});

test('automatic combat uses atomic regeneration, energy, rewards and lease',()=>{
  assert.match(combat,/admin\.rpc\('audit_regen_character'/);
  assert.match(combat,/admin\.rpc\('audit_spend_energy'/);
  assert.match(combat,/admin\.rpc\('audit_apply_progression'/);
  assert.match(combat,/admin\.rpc\('audit_allocate_stat'/);
  assert.match(combat,/admin\.rpc\('audit_acquire_action_lease'/);
  assert.doesNotMatch(combat,/update\(\{energy:Number\(c\.energy\)-amount\}\)/);
});

test('manual combat reward path uses atomic progression',()=>{
  assert.match(manual,/admin\.rpc\('audit_apply_progression'/);
  assert.match(manual,/admin\.rpc\('audit_regen_character'/);
});

test('production fails closed instead of serving local demo economy',()=>{
  assert.match(server,/NODE_ENV.*production|production.*NODE_ENV/s);
  assert.match(server,/503/);
  assert.match(server,/Supabase game backend is not configured|production backend/i);
});

test('fast combat never fabricates victory after result timeout',()=>{
  assert.match(fast,/SIN CONFIRMAR|UNCONFIRMED/);
  assert.match(fast,/confirmed/);
  assert.doesNotMatch(fast,/victory=!\/Bastión\|Bastion\/i/);
});

test('optimistic travel is reconciled against authoritative state',()=>{
  assert.match(hotfix,/authoritative/i);
  assert.match(hotfix,/reconcile/i);
  assert.match(hotfix,/\/api\/state/);
});

test('audit migration adds supporting FK indexes without destructive DDL',()=>{
  assert.match(indexMigration,/create index if not exists/i);
  assert.doesNotMatch(indexMigration,/drop\s+table|truncate|delete\s+from/i);
});
