import test from 'node:test';
import assert from 'node:assert/strict';
import {createDefaultWorld,applyAction} from '../backend/lib/game.mjs';

test('mining consumes energy and adds ore',()=>{const w=createDefaultWorld(),p=w.players.demo,e=p.energy,o=p.resources.ore;applyAction(w,'demo','mine');assert.equal(p.energy,e-5);assert.ok(p.resources.ore>o)});
test('crafting validates and creates gear',()=>{const w=createDefaultWorld(),p=w.players.demo;p.resources.ore=100;p.resources.wood=100;const before=p.inventory.length;applyAction(w,'demo','craft',{recipeId:'iron-blade'});assert.equal(p.inventory.length,before+1)});
test('combat can complete without corrupting state',()=>{const w=createDefaultWorld(),p=w.players.demo;p.stats.atk=100;const r=applyAction(w,'demo','combat',{enemyId:'goblin'});assert.equal(r.ok,true);assert.ok(p.gold>=120)});
test('market purchase removes listing and costs gold',()=>{const w=createDefaultWorld(),p=w.players.demo;const id=w.market[0].id,price=w.market[0].price,count=p.inventory.length;applyAction(w,'demo','buy',{listingId:id});assert.equal(p.gold,120-price);assert.equal(p.inventory.length,count+1);assert.ok(!w.market.some(x=>x.id===id))});
