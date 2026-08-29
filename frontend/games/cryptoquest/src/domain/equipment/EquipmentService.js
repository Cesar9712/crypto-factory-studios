export class EquipmentService {
  constructor({ store, bus }) { this.store=store; this.bus=bus; }
  equip(slot, item) {
    if(!slot||!item) throw new Error('slot and item required');
    let previous=null;
    this.store.update(s=>{ s.player ??= {}; s.player.inventory ??= {items:[],equipped:{}}; s.player.inventory.equipped ??= {}; previous=s.player.inventory.equipped[slot]??null; s.player.inventory.equipped[slot]=structuredClone(item); },{source:'equipment:equip'});
    this.bus?.emit('equipment:changed',{slot,item,previous}); return previous;
  }
  unequip(slot) {
    let item=null; this.store.update(s=>{ item=s.player?.inventory?.equipped?.[slot]??null; if(s.player?.inventory?.equipped) delete s.player.inventory.equipped[slot]; },{source:'equipment:unequip'});
    this.bus?.emit('equipment:changed',{slot,item:null,previous:item}); return item;
  }
  get(slot){ return structuredClone(this.store.select(s=>s.player?.inventory?.equipped?.[slot]??null)); }
}
