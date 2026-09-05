import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const auth=await readFile(new URL('../frontend/auth-confirmation.js',import.meta.url),'utf8');
const index=await readFile(new URL('../frontend/index.html',import.meta.url),'utf8');
const server=await readFile(new URL('../backend/server.mjs',import.meta.url),'utf8');

test('signup confirmation is forced to public Nexus Realms callback',()=>{
  assert.match(auth,/https:\/\/nexus-realms-web3\.onrender\.com/);
  assert.match(auth,/\/auth\/callback/);
  assert.match(auth,/\/auth\/v1\/signup/);
  assert.match(auth,/redirect_to/);
  assert.doesNotMatch(auth,/localhost:3000/);
});

test('auth guard loads before runtime and app modules',()=>{
  const guard=index.indexOf('/auth-confirmation.js');
  const runtime=index.indexOf('/runtime.js');
  const app=index.indexOf('/app.js');
  assert.ok(guard>=0);
  assert.ok(runtime>guard);
  assert.ok(app>guard);
});

test('public callback route serves the game shell',()=>{
  assert.match(server,/url\.pathname==='\/auth\/callback'/);
  assert.match(server,/frontend\/index\.html/);
});

test('callback keeps auth hash for supabase-js session recovery',()=>{
  assert.match(auth,/currentUrl\.hash/);
  assert.match(auth,/email_confirmed/);
  assert.match(auth,/Correo confirmado correctamente/);
  assert.match(auth,/Email confirmed successfully/);
});
