import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const read=p=>readFile(new URL(`../${p}`,import.meta.url),'utf8');

test('performance layer loads before visual and app modules',async()=>{
  const [html,pkg]=await Promise.all([read('frontend/index.html'),read('package.json')]);
  const perf=html.indexOf('/performance.js?v=20260905-5200');
  const visual=html.indexOf('/phase1-visual.js?v=20260905-5000');
  const app=html.indexOf('/app.js?v=');
  assert.ok(perf>=0);
  assert.ok(visual>=0);
  assert.ok(app>=0);
  assert.ok(perf<visual);
  assert.ok(perf<app);
  assert.match(pkg,/frontend\/performance\.js/);
});

test('state requests are shared and cached without polling',async()=>{
  const src=await read('frontend/performance.js');
  assert.match(src,/STATE_TTL=15000/);
  assert.match(src,/pathname==='\/api\/state'/);
  assert.match(src,/inFlight&&inFlight\.auth===meta\.auth/);
  assert.match(src,/freshResponse\(stateCache\)/);
  assert.match(src,/\['\/api\/action','\/api\/reset'\]/);
  assert.match(src,/saveState\(snap,meta\.auth\)/);
  assert.doesNotMatch(src,/setInterval/);
  assert.doesNotMatch(src,/MutationObserver/);
});

test('mobile map rendering uses lightweight GPU rules',async()=>{
  const src=await read('frontend/performance.js');
  assert.match(src,/nexus-mobile-fast/);
  assert.match(src,/backdrop-filter:none/);
  assert.match(src,/content-visibility:auto/);
  assert.match(src,/contain-intrinsic-size:82px/);
  assert.match(src,/p1-travel-transition/);
});
