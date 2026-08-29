import { StateMachine } from '../../core/index.js';

export function createCombatMachine(bus) {
  return new StateMachine({
    initial: 'idle',
    bus,
    context: { combatId: null, turn: 0, actor: null },
    transitions: {
      idle: {
        START: { target: 'playerTurn', action: (ctx, payload) => { ctx.combatId = payload?.combatId ?? crypto.randomUUID(); ctx.turn = 1; ctx.actor = 'player'; } },
      },
      playerTurn: {
        COMMIT_ACTION: { target: 'resolving', action: ctx => { ctx.actor = 'system'; } },
        FLEE: 'finished',
      },
      resolving: {
        ENEMY_TURN: { target: 'enemyTurn', action: ctx => { ctx.actor = 'enemy'; } },
        VICTORY: 'finished',
        DEFEAT: 'finished',
      },
      enemyTurn: {
        RESOLVE_ENEMY: { target: 'resolving', action: ctx => { ctx.actor = 'system'; } },
      },
      finished: {
        RESET: { target: 'idle', action: ctx => { ctx.combatId = null; ctx.turn = 0; ctx.actor = null; } },
      },
    },
  });
}
