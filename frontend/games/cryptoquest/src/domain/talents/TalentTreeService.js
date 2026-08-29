export class TalentTreeService {
  constructor({ store, bus }) { this.store = store; this.bus = bus; }

  registerTree(tree) {
    if (!tree?.id || !Array.isArray(tree.nodes)) throw new Error('Talent tree requires id and nodes');
    this.store.update(state => {
      state.talents ??= { trees: {}, unlocked: {}, points: 0 };
      state.talents.trees[tree.id] = structuredClone(tree);
    }, { source: 'talents:register', treeId: tree.id });
  }

  grantPoints(amount) {
    const delta = Math.max(0, Math.floor(Number(amount) || 0));
    this.store.update(state => {
      state.talents ??= { trees: {}, unlocked: {}, points: 0 };
      state.talents.points = Math.max(0, Number(state.talents.points ?? 0) + delta);
    }, { source: 'talents:grant', amount: delta });
  }

  unlock(treeId, nodeId) {
    let unlocked = false;
    this.store.update(state => {
      state.talents ??= { trees: {}, unlocked: {}, points: 0 };
      const tree = state.talents.trees?.[treeId];
      if (!tree) throw new Error(`Unknown talent tree: ${treeId}`);
      const node = tree.nodes.find(n => n.id === nodeId);
      if (!node) throw new Error(`Unknown talent node: ${nodeId}`);
      const key = `${treeId}:${nodeId}`;
      if (state.talents.unlocked[key]) return;
      const deps = node.requires ?? [];
      for (const dependency of deps) {
        if (!state.talents.unlocked[`${treeId}:${dependency}`]) throw new Error(`Talent dependency missing: ${dependency}`);
      }
      const cost = Math.max(1, Number(node.cost ?? 1));
      if (Number(state.talents.points ?? 0) < cost) throw new Error('Not enough talent points');
      state.talents.points -= cost;
      state.talents.unlocked[key] = { rank: 1, unlockedAt: Date.now() };
      unlocked = true;
    }, { source: 'talents:unlock', treeId, nodeId });
    if (unlocked) this.bus?.emit('talent:unlocked', { treeId, nodeId });
    return unlocked;
  }
}
