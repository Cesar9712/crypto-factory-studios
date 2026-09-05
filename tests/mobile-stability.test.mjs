import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const read=path=>readFile(new URL(`../${path}`,import.meta.url),'utf8');

test('launcher modules do not use broad MutationObserver render loops',async()=>{
  for(const path of ['frontend/clans.js','frontend/earn.js','frontend/season.js','frontend/referrals.js']){
    const source=await read(path);
    assert.doesNotMatch(source,/new\s+MutationObserver\s*\(/,`${path} must stay event-driven`);
  }
});

test('compatibility helper does not monkeypatch MutationObserver',async()=>{
  const source=await read('frontend/mutation-guard.js');
  assert.doesNotMatch(source,/window\.MutationObserver\s*=/);
});

test('release hardening has no permanent polling interval',async()=>{
  const source=await read('frontend/release.js');
  assert.doesNotMatch(source,/setInterval\s*\(/);
});

test('mobile runtime enforces bounded network timeouts',async()=>{
  const source=await read('frontend/runtime.js');
  assert.match(source,/DIRECT_TIMEOUT\s*=\s*9000/);
  assert.match(source,/FALLBACK_TIMEOUT\s*=\s*15000/);
  assert.match(source,/AbortController/);
});
