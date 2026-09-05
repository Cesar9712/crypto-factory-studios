import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const lifecycle=await readFile(new URL('../frontend/phase1-lifecycle.js',import.meta.url),'utf8');
const visual=await readFile(new URL('../frontend/phase1-visual.js',import.meta.url),'utf8');
const index=await readFile(new URL('../frontend/index.html',import.meta.url),'utf8');

test('phase one lifecycle is installed before app render',()=>{
  const hook=index.indexOf('/phase1-lifecycle.js');
  const visualPos=index.indexOf('/phase1-visual.js');
  const app=index.indexOf('/app.js');
  assert.ok(hook>=0);
  assert.ok(visualPos>hook);
  assert.ok(app>visualPos);
});

test('visual world and combat nodes survive base panel rerenders',()=>{
  assert.match(lifecycle,/savedWorld/);
  assert.match(lifecycle,/savedCombat/);
  assert.match(lifecycle,/p1-world/);
  assert.match(lifecycle,/p1-combat-roster/);
  assert.match(lifecycle,/p1-legacy-destinations/);
  assert.match(lifecycle,/p1-legacy-enemies/);
});

test('lifecycle hook is bounded and cannot recursively observe its own renders',()=>{
  assert.doesNotMatch(lifecycle,/MutationObserver/);
  assert.doesNotMatch(lifecycle,/setInterval/);
  assert.doesNotMatch(lifecycle,/requestAnimationFrame/);
  assert.match(lifecycle,/nexus:panel-render/);
});

test('AUTO and MANUAL mode remain persistent and mutually selectable',()=>{
  assert.match(visual,/nexus-combat-mode/);
  assert.match(visual,/data-p1-mode="auto"/);
  assert.match(visual,/data-p1-mode="manual"/);
  assert.match(visual,/setMode\(target\.dataset\.p1Mode\)/);
});
