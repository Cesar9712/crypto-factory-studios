import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const read=p=>readFile(new URL(`../${p}`,import.meta.url),'utf8');

test('Phase 3 UI is loaded without recursive observers or permanent polling',async()=>{
  const [html,client,pkg]=await Promise.all([read('frontend/index.html'),read('frontend/phase3.js'),read('package.json')]);
  assert.match(html,/phase3\.css\?v=20260905-5000/);
  assert.match(html,/phase3\.js\?v=20260905-5000/);
  assert.match(pkg,/frontend\/phase3\.js/);
  assert.match(client,/functions\/v1\/phase3-engine/);
  assert.match(client,/nexus:panel-render/);
  assert.doesNotMatch(client,/new MutationObserver/);
  assert.doesNotMatch(client,/setInterval/);
  assert.match(client,/\['weapon','helmet','armor','gloves','boots','ring'\]/);
  assert.match(client,/data-p3-unequip/);
  assert.match(client,/mutate\('equip',\{itemId:b\.dataset\.equip\}\)/);
  assert.match(client,/strip\.innerHTML!==stripHtml/);
  assert.match(client,/wrap\.innerHTML!==extraHtml/);
  assert.match(client,/bonusRow\('2P'/);
  assert.match(client,/bonusRow\('4P'/);
  assert.match(client,/bonusRow\('6P'/);
});

test('Phase 3 schema defines sets, specializations, six slots and internal respec',async()=>{
  const sql=await read('database/migrations/20260905_phase3_sets_specializations_builds.sql');
  for(const id of ['ash_lord','iron_bastion','ember_savant','frost_weaver','storm_marksman','wild_hunter','night_reaper','venomfang','riftwalker','wayfarer']) assert.match(sql,new RegExp(`'${id}'`));
  for(const id of ['guardian','berserker','gladiator','pyromancer','cryomancer','arcanist','marksman','hunter','scout','venom','shadow','executioner']) assert.match(sql,new RegExp(`'${id}'`));
  assert.match(sql,/helmet_item_id/);
  assert.match(sql,/gloves_item_id/);
  assert.match(sql,/phase3_build_profile/);
  assert.match(sql,/pieces>=2/);
  assert.match(sql,/pieces>=4/);
  assert.match(sql,/pieces>=6/);
  assert.match(sql,/gold_cost:=least\(2000,400\+c\.specialization_respec_count\*200\)/);
  assert.match(sql,/essence_cost:=least\(10,3\+c\.specialization_respec_count\)/);
  assert.doesNotMatch(sql,/usd|usdt|payment|withdraw/i);
});

test('Phase 3 engines preserve base skills and apply builds in PvE, manual and PvP',async()=>{
  const [p3,combat,manual,p2]=await Promise.all([
    read('supabase/functions/phase3-engine/index.ts'),
    read('supabase/functions/combat-engine/index.ts'),
    read('supabase/functions/manual-combat/index.ts'),
    read('supabase/functions/phase2-engine/index.ts')
  ]);
  assert.match(p3,/phase3_build_profile/);
  assert.match(p3,/op==='specialize'/);
  assert.match(p3,/op==='equip'/);
  assert.match(p3,/op==='unequip'/);
  assert.match(combat,/const base=/);
  assert.match(combat,/return\[\.\.\.base,\.\.\.spec\]/);
  assert.match(combat,/phase3_award_set_drop/);
  assert.match(manual,/phase3_specialization_skills/);
  assert.match(manual,/phase3_award_set_drop/);
  assert.match(p2,/phase3_build_profile/);
  assert.match(p2,/loadFighter\(c\.id,true\)/);
  assert.match(p2,/incoming\(dmg,b\)/);
  assert.match(p2,/actualRatio>2\.4/);
});
