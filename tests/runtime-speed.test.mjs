import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const read=p=>readFile(new URL(`../${p}`,import.meta.url),'utf8');

test('runtime keeps authoritative state warm for navigation',async()=>{
  const src=await read('frontend/runtime.js');
  assert.match(src,/const STATE_TTL=15000/);
  assert.match(src,/async function storeStateSnapshot/);
  assert.match(src,/if\(!data\?\.player\|\|!data\?\.zones\)return false/);
  assert.match(src,/stateCache=\{body,status:res\.status/);
  assert.match(src,/window\.__NEXUS_STATE__=data/);
  assert.match(src,/emit\('nexus:state',\{state:data,source\}\)/);
});

test('successful game actions reuse returned state instead of forcing an immediate refetch',async()=>{
  const src=await read('frontend/runtime.js');
  assert.match(src,/const cached=await storeStateSnapshot\(res,'action'\)/);
  assert.match(src,/if\(!cached\)\{stateCache=null;stateCacheAt=0;\}/);
  assert.doesNotMatch(src,/else if\(isAction&&res\.ok\)\{stateCache=null;stateCacheAt=0;captureState/);
});
