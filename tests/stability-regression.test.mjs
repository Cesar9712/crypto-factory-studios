import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const read=p=>readFile(new URL(`../${p}`,import.meta.url),'utf8');

test('runtime prevents stale state reads from overwriting travel actions',async()=>{
  const src=await read('frontend/runtime.js');
  assert.match(src,/let mutationEpoch=0/);
  assert.match(src,/let activeMutations=0/);
  assert.match(src,/if\(isState&&activeMutations>0\)return jsonResponse\(\{error:'STATE_REFRESH_DEFERRED'\},409\)/);
  assert.match(src,/if\(isState&&requestEpoch!==mutationEpoch\)/);
  assert.match(src,/STALE_STATE_DISCARDED/);
  assert.match(src,/window\.__nexusPerf\?\.invalidateState\?\.\(\)/);
});

test('performance cache cannot be repopulated by a pre-action state request',async()=>{
  const src=await read('frontend/performance.js');
  assert.match(src,/let mutationEpoch=0/);
  assert.match(src,/inFlight&&inFlight\.auth===meta\.auth&&inFlight\.epoch===epoch/);
  assert.match(src,/epoch===mutationEpoch\?saveState\(s,meta\.auth\):s/);
  assert.match(src,/invalidateState\(\)\{mutationEpoch\+=1;stateCache=null;inFlight=null\}/);
});

test('More launchers are rehydrated after panel replacement with a narrow observer',async()=>{
  const src=await read('frontend/mutation-guard.js');
  assert.match(src,/new MutationObserver/);
  assert.match(src,/observe\(panel,\{childList:true\}\)/);
  assert.doesNotMatch(src,/subtree:true/);
  assert.match(src,/\[data-tab\],\[data-more\]/);
  assert.match(src,/source:'more-refresh'/);
});
