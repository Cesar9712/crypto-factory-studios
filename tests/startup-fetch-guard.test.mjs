import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const read=p=>readFile(new URL(`../${p}`,import.meta.url),'utf8');
const guard=await read('frontend/startup-fetch-guard.js');
const index=await read('frontend/index.html');

test('startup guard loads before performance and app modules',()=>{
  const guardPos=index.indexOf('/startup-fetch-guard.js');
  const perfPos=index.indexOf('/performance.js');
  const appPos=index.indexOf('/app.js');
  assert.ok(guardPos>=0,'startup guard missing from index');
  assert.ok(perfPos>guardPos,'startup guard must load before performance wrapper');
  assert.ok(appPos>perfPos,'app should still load after performance layer');
});

test('startup guard only retries boot GET state requests',()=>{
  assert.match(guard,/pathname==='\/api\/state'/);
  assert.match(guard,/method==='GET'/);
  assert.match(guard,/BOOT_WINDOW_MS=15000/);
  assert.match(guard,/RETRY_DELAYS_MS=\[250,650\]/);
  assert.doesNotMatch(guard,/setInterval/);
});

test('startup retry is bounded and limited to transient failures',()=>{
  assert.match(guard,/status===500\|\|status===502\|\|status===503\|\|status===504/);
  assert.match(guard,/request\[_ \]failed\|upstream/);
  assert.match(guard,/attempt<=RETRY_DELAYS_MS\.length/);
  assert.match(guard,/maxAttempts:RETRY_DELAYS_MS\.length\+1/);
});

test('non-transient responses are returned immediately',()=>{
  assert.match(guard,/if\(!\(await transientBody\(response\)\)\|\|attempt===RETRY_DELAYS_MS\.length\)return response/);
});
