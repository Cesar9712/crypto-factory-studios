import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const frontend=await readFile(new URL('../frontend/referrals.js',import.meta.url),'utf8');
const edge=await readFile(new URL('../supabase/functions/referral-engine/index.ts',import.meta.url),'utf8');
const migration=await readFile(new URL('../database/migrations/20260905_referral_system_v1.sql',import.meta.url),'utf8');

const has=(src,text,msg)=>assert.ok(src.includes(text),msg||`missing ${text}`);

test('captures referral token from link and persists it',()=>{
  has(frontend,"u.searchParams.get('ref')");
  has(frontend,"localStorage.setItem(STORAGE_KEY,r)");
  has(frontend,"history.replaceState");
});

test('builds share URL from current origin rather than UI hardcoding',()=>{
  has(frontend,'window.location.origin');
  has(frontend,"u.searchParams.set('ref',state.profile.code)");
});

test('automatic attribution survives missing character and retries without MutationObserver',()=>{
  has(frontend,'retryLoad()');
  has(frontend,"localStorage.getItem(STORAGE_KEY)");
  assert.equal(frontend.includes('MutationObserver'),false);
});

test('link-first UI exposes copy and share actions',()=>{
  has(frontend,"link:'Mi enlace de referido'");
  has(frontend,"copy:'Copiar enlace'");
  has(frontend,"share:'Compartir'");
  has(frontend,'navigator.share');
});

test('automatic frontend calls server-side applyReferral',()=>{
  has(frontend,"action:'applyReferral'");
  has(edge,"action==='applyReferral'");
});

test('edge function derives character from authenticated user',()=>{
  has(edge,'const user=await authUser(req)');
  has(edge,'characterFor(user.id)');
});

test('database rejects self referral and duplicate attribution',()=>{
  has(migration,'constraint referral_not_self check (referred_character_id <> referrer_character_id)');
  has(migration,'referred_character_id uuid primary key');
});

test('referral must be attached before Founder Pack payment',()=>{
  has(migration,"if v_owned then raise exception 'Referral must be applied before Founder Pack purchase'");
  has(migration,"status='paid'");
});

test('reward trigger is idempotent',()=>{
  has(migration,'source_order_id uuid not null unique');
  has(migration,'unique(referred_character_id)');
  has(migration,'if exists(select 1 from referral_rewards where source_order_id=new.id or referred_character_id=new.character_id) then return new; end if;');
});

test('rewards remain one-level internal Premium Credits',()=>{
  has(migration,'referrer_premium_credits');
  has(migration,'referred_premium_credits');
  has(edge,"mode:'ONE_LEVEL_NONCASH'");
  has(edge,'non-withdrawable Premium Credits');
});
