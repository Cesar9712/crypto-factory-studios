import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const js=await readFile(new URL('../frontend/phase2.js',import.meta.url),'utf8');
const css=await readFile(new URL('../frontend/phase2.css',import.meta.url),'utf8');
const index=await readFile(new URL('../frontend/index.html',import.meta.url),'utf8');

test('Phase 2 assets load after Phase 1 without replacing it',()=>{
  assert.match(index,/phase1-visual\.js/);
  assert.match(index,/phase1-auto-fast\.js/);
  assert.match(index,/phase2\.js/);
  assert.match(index,/phase2\.css/);
  assert.ok(index.indexOf('/phase2.js')>index.indexOf('/phase1-auto-fast.js'));
});

test('Phase 2 uses authenticated server engine for rifts and arena',()=>{
  assert.match(js,/functions\/v1\/phase2-engine/);
  assert.match(js,/authorization/);
  assert.match(js,/rift_state/);
  assert.match(js,/rift_start/);
  assert.match(js,/rift_advance/);
  assert.match(js,/arena_state/);
  assert.match(js,/arena_match/);
});

test('combat feature selector exposes adventure rifts and arena',()=>{
  assert.match(js,/nexus-combat-feature/);
  assert.match(js,/data-p2-feature=\"adventure\"/);
  assert.match(js,/data-p2-feature=\"rifts\"/);
  assert.match(js,/data-p2-feature=\"arena\"/);
});

test('rift generation seed is never supplied by the client',()=>{
  assert.match(js,/rift_start',\{tier,difficulty\}/);
  assert.doesNotMatch(js,/rift_start',\{[^}]*seed/);
});

test('arena creates per-match replay key and reuses Phase 1 battle visuals',()=>{
  assert.match(js,/requestKey:crypto\.randomUUID\(\)/);
  assert.match(js,/p1-battle-stage/);
  assert.match(js,/p1-fighters/);
  assert.match(js,/p1-result/);
});

test('Phase 2 avoids recursive observers and permanent polling',()=>{
  assert.doesNotMatch(js,/MutationObserver/);
  assert.doesNotMatch(js,/setInterval/);
  assert.doesNotMatch(js,/requestAnimationFrame/);
  assert.match(js,/nexus:panel-render/);
});

test('mobile layout and phase switching hide legacy combat safely',()=>{
  assert.match(css,/p2-mode-rifts/);
  assert.match(css,/p2-mode-arena/);
  assert.match(css,/@media\(max-width:620px\)/);
  assert.match(css,/#p1-combat-roster/);
});
