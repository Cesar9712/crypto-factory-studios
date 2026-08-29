export class PlayerProgressService {
  constructor({ store, bus }) { this.store = store; this.bus = bus; }

  ensurePlayer() {
    const player = this.store.select(state => state.player);
    if (!player) throw new Error('Player state is not initialized');
    return player;
  }

  grantXp(amount, resolver = null) {
    const xpGain = Math.max(0, Number(amount) || 0);
    let result = null;
    this.store.update(state => {
      if (!state.player) throw new Error('Player state is not initialized');
      const player = state.player;
      player.level = Math.max(1, Number(player.level ?? 1));
      player.xp = Math.max(0, Number(player.xp ?? 0) + xpGain);
      if (typeof resolver === 'function') {
        const resolved = resolver({ level: player.level, xp: player.xp });
        if (resolved && Number.isFinite(resolved.level) && Number.isFinite(resolved.xp)) {
          player.level = Math.max(1, Math.floor(resolved.level));
          player.xp = Math.max(0, resolved.xp);
        }
      }
      result = { level: player.level, xp: player.xp, gained: xpGain };
    }, { source: 'player:xp', amount: xpGain });
    this.bus?.emit('player:xp-changed', result);
    return result;
  }

  addCurrency(currency, amount) {
    const delta = Number(amount) || 0;
    let balance = 0;
    this.store.update(state => {
      if (!state.player) throw new Error('Player state is not initialized');
      state.player.currencies ??= {};
      state.player.currencies[currency] = Math.max(0, Number(state.player.currencies[currency] ?? 0) + delta);
      balance = state.player.currencies[currency];
    }, { source: 'player:currency', currency, amount: delta });
    this.bus?.emit('player:currency-changed', { currency, amount: delta, balance });
    return balance;
  }

  setVitals(vitals) {
    this.store.update(state => {
      if (!state.player) throw new Error('Player state is not initialized');
      state.player.vitals ??= {};
      for (const [key, value] of Object.entries(vitals ?? {})) {
        if (Number.isFinite(Number(value))) state.player.vitals[key] = Number(value);
      }
    }, { source: 'player:vitals' });
  }
}
