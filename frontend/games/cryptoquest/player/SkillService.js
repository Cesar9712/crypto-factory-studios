export class SkillService {
  constructor({ store, bus }) { this.store = store; this.bus = bus; }
  register(skill) { if(!skill?.id) throw new Error('Skill id required');this.store.update(s=>{s.skills??={definitions:{},unlocked:{},levels:{},cooldowns:{}};s.skills.definitions[skill.id]=structuredClone(skill);},{source:'skills:register'}); }
  unlock(id) { const exists=this.store.select(s=>Boolean(s.skills?.definitions?.[id]));if(!exists)throw new Error(`Unknown skill: ${id}`);this.store.update(s=>{s.skills.unlocked[id]=true;s.skills.levels[id]??=1;},{source:'skills:unlock'});this.bus?.emit('skill:unlocked',{id}); }
  upgrade(id,maxLevel=10) { this.store.update(s=>{if(!s.skills?.unlocked?.[id])throw new Error('Skill locked');const n=s.skills.levels[id]??1;if(n>=maxLevel)throw new Error('Skill max level');s.skills.levels[id]=n+1;},{source:'skills:upgrade'}); }
  setCooldown(id,until) { this.store.update(s=>{s.skills??={definitions:{},unlocked:{},levels:{},cooldowns:{}};s.skills.cooldowns[id]=Math.max(0,Number(until)||0);},{source:'skills:cooldown'}); }
  ready(id,now=Date.now()) { return (this.store.select(s=>s.skills?.cooldowns?.[id])??0)<=now; }
}
