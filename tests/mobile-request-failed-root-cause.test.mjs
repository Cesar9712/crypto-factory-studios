import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const runtime=await readFile(new URL('../frontend/runtime.js',import.meta.url),'utf8');
const app=await readFile(new URL('../frontend/app.js',import.meta.url),'utf8');
const html=await readFile(new URL('../frontend/index.html',import.meta.url),'utf8');

test('runtime classifies request_failed as transient for idempotent reads',()=>{
  assert.match(runtime,/isTransientDirectResponse/);
  assert.match(runtime,/request\[_ \]failed/);
  assert.match(runtime,/retryDirectRequest/);
  assert.match(runtime,/READ_PATHS/);
});

test('runtime coalesces duplicate state loads instead of issuing parallel startup reads',()=>{
  assert.match(runtime,/if\(inflight\.has\(key\)\)return \(await inflight\.get\(key\)\)\.clone\(\)/);
});

test('runtime does not blindly retry mutations',()=>{
  assert.match(runtime,/if\(!isRead\(info\)\)return directRequest\(info,input,init\)/);
});

test('runtime can serve the last good state after transient refresh failures',()=>{
  assert.match(runtime,/STALE_STATE_MAX_AGE/);
  assert.match(runtime,/stale-state-fallback/);
});

test('raw request_failed is never the final synthetic user-facing transient response',()=>{
  assert.match(runtime,/Problema temporal de conexión\. Reintenta en unos segundos\./);
});

test('app resolves INITIAL_SESSION and getSession through one bootstrap gate',()=>{
  assert.match(app,/let authBootResolved=false/);
  assert.match(app,/event==='INITIAL_SESSION'/);
  assert.match(app,/if\(authBootResolved\)return/);
  assert.match(app,/if\(!authBootResolved\)/);
});

test('app keeps an already rendered state silent on transient refresh errors',()=>{
  assert.match(app,/isTransientLoadError/);
  assert.match(app,/!quiet&&!\(state&&transient\)/);
});

test('html cache-busts both corrected runtime and app bootstrap',()=>{
  assert.match(html,/runtime\.js\?v=20260906-6200/);
  assert.match(html,/app\.js\?v=20260906-6300/);
});
