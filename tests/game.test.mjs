import test from 'node:test';
import assert from 'node:assert/strict';
import {createDefaultWorld,applyAction,tickState} from '../backend/lib/game.mjs';

test('mining consumes energy and adds ore',()=>{const w=createDefaultWorld(),p=w.players.demo,e=p.energy,o=p.resources.ore;applyAction(w,'demo','mine');assert.equal(p.energy,e-5);assert.ok(p.resources.ore>o)});
test('crafting validates and creates gear',()=>{const w=createDefaultWorld(),p=w.players.demo;p.resources.ore=100;p.resources.wood=100;const before=p.inventory.length;applyAction(w,'demo','craft',{recipeId:'iron-blade'});assert.equal(p.inventory.length,before+1)});
test('crafting does not spend energy when materials are missing',()=>{const w=createDefaultWorld(),p=w.players.demo;p.resources.ore=0;const energy=p.energy;assert.throws(()=>applyAction(w,'demo','craft',{recipeId:'iron-blade'}),/Need 20 ore/);assert.equal(p.energy,energy)});
test('rest uses timed regeneration instead of instant refill',()=>{const w=createDefaultWorld(),p=w.players.demo;p.energy=20;p.hp=10;applyAction(w,'demo','rest');assert.equal(p.energy,20);assert.equal(p.hp,10);p.lastTick-=60000;tickState(p);assert.ok(p.energy>20);assert.ok(p.hp>10)});
test('unknown combat target is rejected',()=>{const w=createDefaultWorld();assert.throws(()=>applyAction(w,'demo','combat',{enemyId:'not-real'}),/Unknown enemy/)});
test('combat can complete without corrupting state',()=>{const w=createDefaultWorld(),p=w.players.demo;p.stats.atk=100;const r=applyAction(w,'demo','combat',{enemyId:'goblin'});assert.equal(r.ok,true);assert.ok(p.gold>=120);assert.ok(p.hp>=1&&p.hp<=p.maxHp)});
test('market purchase removes listing and costs gold',()=>{const w=createDefaultWorld(),p=w.players.demo;const id=w.market[0].id,price=w.market[0].price,count=p.inventory.length;applyAction(w,'demo','buy',{listingId:id});assert.equal(p.gold,120-price);assert.equal(p.inventory.length,count+1);assert.ok(!w.market.some(x=>x.id===id))});
test('wallet input validates an EVM address',()=>{const w=createDefaultWorld();assert.throws(()=>applyAction(w,'demo','wallet',{address:'not-a-wallet'}),/Invalid EVM wallet address/);const good='0x1111111111111111111111111111111111111111';applyAction(w,'demo','wallet',{address:good});assert.equal(w.players.demo.wallet,good)});
