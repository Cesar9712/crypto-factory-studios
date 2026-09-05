import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const js=await readFile(new URL('../frontend/phase1-visual.js',import.meta.url),'utf8');
const css=await readFile(new URL('../frontend/phase1-visual.css',import.meta.url),'utf8');
const index=await readFile(new URL('../frontend/index.html',import.meta.url),'utf8');

test('phase one loads visual world and combat assets',()=>{
  assert.match(index,/phase1-visual\.css/);
  assert.match(index,/phase1-visual\.js/);
});

test('manual combat uses authenticated server edge function',()=>{
  assert.match(js,/functions\/v1\/manual-combat/);
  assert.match(js,/authorization/);
  assert.match(js,/op,payload/);
  assert.match(js,/manualCall\('turn'/);
});

test('combat exposes AUTO and MANUAL without client damage calculation',()=>{
  assert.match(js,/nexus-combat-mode/);
  assert.match(js,/data-p1-mode="auto"/);
  assert.match(js,/data-p1-mode="manual"/);
  assert.doesNotMatch(js,/Math\.random\(/);
});

test('visual layer avoids recursive observers and unbounded animation loops',()=>{
  assert.doesNotMatch(js,/MutationObserver/);
  assert.doesNotMatch(js,/requestAnimationFrame/);
  assert.doesNotMatch(js,/setInterval/);
});

test('world route and battle stage are present and mobile styled',()=>{
  assert.match(js,/p1-route/);
  assert.match(js,/p1-battle-stage/);
  assert.match(css,/@media\(max-width:620px\)/);
  assert.match(css,/p1-float/);
  assert.match(css,/p1-boss-warning/);
});
