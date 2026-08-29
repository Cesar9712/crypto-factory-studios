export class EnergyService {
  constructor({ store, bus, now = () => Date.now() }) { this.store = store; this.bus = bus; this.now = now; }
  snapshot() { return this.store.select(s => structuredClone(s.player?.energy ?? null)); }
  canSpend(cost) { const energy = this.store.select(s => s.player?.energy); return Boolean(energy && Number.isFinite(cost) && cost >= 0 && energy.current >= cost); }
  spend(cost, reason = 'action') {
    if (!this.canSpend(cost)) return false;
    this.store.update(state => { state.player.energy.current = Math.max(0, state.player.energy.current - cost); state.player.energy.updatedAt = this.now(); }, { source: 'energy-service', reason, cost });
    this.bus?.emit('energy:spent', { cost, reason, at: this.now() });
    return true;
  }
  restore(amount, reason = 'recovery') {
    if (!Number.isFinite(amount) || amount <= 0) return false;
    const exists = this.store.select(state => Boolean(state.player?.energy));
    if (!exists) return false;
    this.store.update(state => { const energy = state.player.energy; energy.current = Math.min(energy.max, energy.current + amount); energy.updatedAt = this.now(); }, { source: 'energy-service', reason, amount });
    this.bus?.emit('energy:restored', { amount, reason, at: this.now() });
    return true;
  }
}
