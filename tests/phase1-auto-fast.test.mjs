import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const js=await readFile(new URL('../frontend/phase1-auto-fast.js',import.meta.url),'utf8');
const index=await readFile(new URL('../frontend/index.html',import.meta.url),'utf8');

test('fast AUTO handler loads after phase one visual combat',()=>{
  const visual=index.indexOf('/phase1-visual.js');
  const fast=index.indexOf('/phase1-auto-fast.js');
  assert.ok(visual>=0);
  assert.ok(fast>visual);
});

test('AUTO result path intercepts visual fight and reuses authoritative legacy combat action',()=>{
  assert.match(js,/mode\(\)!=='auto'/);
  assert.match(js,/stopImmediatePropagation/);
  assert.match(js,/\.enemy-list \[data-enemy=/);
  assert.match(js,/legacy\.click\(\)/);
});

test('AUTO result path is bounded and does not replay turn animations',()=>{
  assert.match(js,/for\(let i=0;i<80;i\+\+\)/);
  assert.match(js,/await wait\(50\)/);
  assert.doesNotMatch(js,/animateLogs/);
  assert.doesNotMatch(js,/MutationObserver/);
  assert.doesNotMatch(js,/requestAnimationFrame/);
  assert.doesNotMatch(js,/setInterval/);
});
