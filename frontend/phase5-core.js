export const PET_RARITIES=['common','uncommon','rare','epic','legendary','mythic'];
export const PHASE5_TABS=['pets','social','rankings','events','achievements','codex'];
export const RANKING_KEYS=['level','power','arena','world_boss','clans','professions','collection','season'];
export const CODEX_CATEGORIES=['monsters','bosses','equipment','sets','pets','resources','zones'];
export function plainText(input,max=280){return String(input??'').replace(/[<>\u0000-\u001f]/g,'').replace(/\s+/g,' ').trim().slice(0,max)}
export function petLevelFromXp(xp,max=50){return Math.min(max,1+Math.floor(Math.sqrt(Math.max(0,Number(xp)||0)/100)))}
export function petEvolutionRequirement(def,stage=0){const s=Math.max(0,Number(stage)||0);return{level:Number(def?.evolution_level||20)+s*10,resource:def?.evolution_resource_key||'essence',amount:Number(def?.evolution_resource_amount||80)*(s+1),item:def?.evolution_item_id||'pet_evolution_core'}}
export function isOnline(lastSeenAt,now=Date.now()){const t=new Date(lastSeenAt||0).getTime();return Number.isFinite(t)&&now-t<5*60_000}
export function eventState(event,now=Date.now()){const s=new Date(event?.starts_at||0).getTime(),e=new Date(event?.ends_at||0).getTime();if(now<s)return'scheduled';if(now>=e)return'ended';return'active'}
