export class EquipmentService {
  constructor({ store, bus }) { this.store = store; this.bus = bus; }
  equippedUid(slot) { return this.store.select(s => s.player?.inventory?.equipped?.[slot] ?? null); }
  equippedItem(slot) { const uid=this.equippedUid(slot); if(!uid) return null; const item=this.store.select(s=>s.player?.inventory?.items?.find(entry=>entry.uid===uid)??null); return item?structuredClone(item):null; }
  equip(slot,uid) { if(!slot||!uid) throw new Error('slot and uid required'); const exists=this.store.select(s=>Boolean(s.player?.inventory?.items?.some(item=>item.uid===uid))); if(!exists) throw new Error(`Item not found: ${uid}`); const previous=this.equippedUid(slot); this.store.update(s=>{s.player??={};s.player.inventory??={items:[],equipped:{}};s.player.inventory.equipped??={};s.player.inventory.equipped[slot]=uid;},{source:'equipment:equip',slot,uid}); this.bus?.emit('equipment:changed',{slot,uid,previous}); return previous; }
  unequip(slot) { const previous=this.equippedUid(slot); if(previous===null) return null; this.store.update(s=>{if(s.player?.inventory?.equipped) delete s.player.inventory.equipped[slot];},{source:'equipment:unequip',slot}); this.bus?.emit('equipment:changed',{slot,uid:null,previous}); return previous; }
}
