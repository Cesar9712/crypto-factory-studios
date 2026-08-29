export class InventoryService {
  constructor({ store, bus }) {
    this.store = store;
    this.bus = bus;
  }

  items() { return this.store.select(s => structuredClone(s.player?.inventory?.items ?? [])); }
  equipped() { return this.store.select(s => structuredClone(s.player?.inventory?.equipped ?? {})); }

  find(uid) { return this.store.select(s => s.player?.inventory?.items?.find(item => item.uid === uid) ?? null); }

  add(item) {
    if (!item?.uid) throw new Error('Inventory item requires uid');
    if (this.find(item.uid)) throw new Error(`Duplicate inventory uid: ${item.uid}`);
    this.store.update(state => {
      state.player ??= {};
      state.player.inventory ??= { items: [], equipped: {} };
      state.player.inventory.items.push(structuredClone(item));
    }, { source: 'inventory-service', action: 'add', uid: item.uid });
    this.bus.emit('inventory:changed', { action: 'add', uid: item.uid });
  }

  remove(uid) {
    let removed = null;
    this.store.update(state => {
      const items = state.player?.inventory?.items ?? [];
      const index = items.findIndex(item => item.uid === uid);
      if (index >= 0) removed = items.splice(index, 1)[0];
      const equipped = state.player?.inventory?.equipped ?? {};
      for (const [slot, equippedUid] of Object.entries(equipped)) if (equippedUid === uid) delete equipped[slot];
    }, { source: 'inventory-service', action: 'remove', uid });
    if (removed) this.bus.emit('inventory:changed', { action: 'remove', uid });
    return removed;
  }

  equip(uid, slot) {
    const item = this.find(uid);
    if (!item) throw new Error(`Item not found: ${uid}`);
    if (!slot) throw new Error('Equipment slot is required');
    this.store.update(state => {
      state.player.inventory.equipped ??= {};
      state.player.inventory.equipped[slot] = uid;
    }, { source: 'inventory-service', action: 'equip', uid, slot });
    this.bus.emit('inventory:changed', { action: 'equip', uid, slot });
  }

  unequip(slot) {
    this.store.update(state => { if (state.player?.inventory?.equipped) delete state.player.inventory.equipped[slot]; }, { source: 'inventory-service', action: 'unequip', slot });
    this.bus.emit('inventory:changed', { action: 'unequip', slot });
  }
}
