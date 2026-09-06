import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {buildingQuote,serverClockOffset,remainingMs,storageCap,offlineCapHours,missionTargets,BUILDING_KEYS} from '../frontend/phase4-core.js';
const read=p=>readFile(new URL(`../${p}`,import.meta.url),'utf8');

test('Bastion upgrade costs and time rise predictably',()=>{
  const def={building_key:'fortress',base_gold:100,base_seconds:120,primary_resource:'ore',secondary_resource:'wood'};
  const a=buildingQuote(def,1),b=buildingQuote(def,2);
  assert.equal(a.next,2);assert.equal(b.next,3);assert.ok(b.gold>a.gold);assert.ok(b.seconds>a.seconds);assert.ok(a.resources.ore>0);assert.ok(a.resources.wood>0);
});

test('Bastion countdown uses server offset, not the phone clock as authority',()=>{
  const client=1_000_000,server=new Date(client+5000).toISOString(),finish=new Date(client+65000).toISOString();
  const offset=serverClockOffset(server,client);assert.equal(offset,5000);assert.equal(remainingMs(finish,offset,client),60000);
});

test('Bastion storage and offline production are capped',()=>{
  assert.equal(storageCap(1,1),320);assert.equal(offlineCapHours(1,1),6);assert.equal(offlineCapHours(99,99),12);assert.ok(storageCap(5,4)>storageCap(1,1));
});

test('Phase 4 defines all nine Bastion buildings',()=>{
  assert.deepEqual(BUILDING_KEYS,['fortress','blacksmith','laboratory','garden','mine','pond','warehouse','market','altar']);
});

test('Clan collective mission scales to the requested 20-member reference',()=>{
  assert.deepEqual(missionTargets(20),{combats:290,resources:5000,crafts:200,bosses:100});
});

test('Phase 4 schema is server authoritative, bounded and internal-only',async()=>{
  const [sql,fix]=await Promise.all([read('database/migrations/20260906_phase4_bastion_clans2.sql'),read('database/migrations/20260906_phase4_bastion_settle_fix.sql')]);
  for(const k of BUILDING_KEYS)assert.match(sql,new RegExp(`'${k}'`));
  assert.match(sql,/upgrade_started_at timestamptz/);assert.match(sql,/upgrade_finishes_at timestamptz/);assert.match(sql,/now\(\)\+v_seconds\*interval '1 second'/);
  assert.match(sql,/phase4_storage_cap/);assert.match(sql,/phase4_offline_cap_hours/);assert.match(sql,/least\(12,4/);assert.match(fix,/v_ticks\*r\.production_per_hour\*r\.level\/6\.0/);
  assert.doesNotMatch(sql,/usdt|withdrawal|wallet_address|chain_tx|custody/i);
});

test('Clans 2.0 extends treasury, research, missions, shop, wars and anti-abuse logs',async()=>{
  const sql=await read('database/migrations/20260906_phase4_bastion_clans2.sql');
  for(const table of ['guild_treasury_resources','guild_research','guild_buffs','guild_mission_progress','guild_shop_purchases','guild_audit_log','guild_wars'])assert.match(sql,new RegExp(`public\\.${table}`));
  for(const research of ['xp_boost','gathering','crafting','boss_damage'])assert.match(sql,new RegExp(`'${research}'`));
  for(const action of ['donation','research_spend','buff_spend','role_change','kick','leadership_transfer'])assert.match(sql,new RegExp(`'${action}'`));
  assert.match(sql,/v_role not in \('leader','officer'\)/);assert.match(sql,/v_role='officer' and v_target_role<>'member'/);
});

test('Existing clan create join leave and boss flows remain in place',async()=>{
  const clans=await read('frontend/clans.js');
  assert.match(clans,/act\('create'/);assert.match(clans,/act\('join'/);assert.match(clans,/act\('leave'/);assert.match(clans,/act\('raidAttack'/);assert.match(clans,/act\('claimRaid'/);
});

test('Phase 4 engine exposes required Bastion and Clan actions',async()=>{
  const edge=await read('supabase/functions/phase4-engine/index.ts');
  for(const action of ['bastionUpgrade','bastionClaim','bastionAltar','clanDonate','clanResearch','clanBuff','clanMissionClaim','clanShopBuy','clanSetRole','clanKick','clanTransfer'])assert.match(edge,new RegExp(`name==='${action}'`));
  assert.match(edge,/serverNow:new Date\(\)\.toISOString\(\)/);assert.match(edge,/phase4_ensure_war/);assert.match(edge,/bossRanking/);
});

test('Phase 4 UI has touchable Bastion buildings and real role controls',async()=>{
  const ui=await read('frontend/phase4.js');
  assert.match(ui,/data-building=/);assert.match(ui,/data-p4-upgrade/);assert.match(ui,/data-phase4-finish/);assert.match(ui,/data-p4-role/);assert.match(ui,/data-p4-kick/);assert.match(ui,/data-p4-transfer/);assert.match(ui,/data-p4-research/);assert.match(ui,/data-p4-mission/);assert.match(ui,/Clan Wars/);
  assert.match(ui,/nexus:panel-render/);assert.doesNotMatch(ui,/new MutationObserver/);
});
