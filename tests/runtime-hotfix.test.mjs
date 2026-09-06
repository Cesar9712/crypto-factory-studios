import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const hotfix=fs.readFileSync('frontend/runtime-hotfix.js','utf8');
const index=fs.readFileSync('frontend/index.html','utf8');

test('runtime hotfix rehydrates Phase 4 after state/action rerenders',()=>{
  assert.match(hotfix,/nexus:panel-render/);
  assert.match(hotfix,/nexus:more-refresh/);
  assert.match(hotfix,/\/api\/state/);
  assert.match(hotfix,/\/api\/action/);
  assert.match(hotfix,/phase4-launcher/);
});

test('fast travel uses optimistic UI and bypasses the slower visual travel handler',()=>{
  assert.match(hotfix,/optimisticTravel/);
  assert.match(hotfix,/data-p1-travel/);
  assert.match(hotfix,/stopImmediatePropagation/);
  assert.match(hotfix,/legacy\.onclick\.call/);
  assert.match(hotfix,/280/);
});

test('hotfix loads before phase1 visual module',()=>{
  const h=index.indexOf('/runtime-hotfix.js');
  const p=index.indexOf('/phase1-visual.js');
  assert.ok(h>=0,'runtime hotfix must be loaded');
  assert.ok(p>=0,'phase1 visual must be loaded');
  assert.ok(h<p,'runtime hotfix must register its capture handler first');
});
