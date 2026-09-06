export const BUILDING_KEYS=['fortress','blacksmith','laboratory','garden','mine','pond','warehouse','market','altar'];
export const BUILDING_ICONS={fortress:'🏰',blacksmith:'⚒️',laboratory:'⚗️',garden:'🌿',mine:'⛏️',pond:'🐟',warehouse:'📦',market:'🏪',altar:'✨'};
export function buildingQuote(def,level){
  const next=Math.max(2,Number(level||1)+1);
  const baseGold=Math.max(1,Number(def?.base_gold||100));
  const baseSeconds=Math.max(30,Number(def?.base_seconds||180));
  const primary=def?.primary_resource||'ore';
  const secondary=def?.secondary_resource||'wood';
  const gold=Math.ceil(baseGold*Math.pow(next,1.55));
  const primaryAmount=Math.ceil((8+baseGold/70)*next);
  const secondaryAmount=Math.ceil(4*next);
  const essence=['fortress','laboratory','altar'].includes(def?.building_key)&&next>=4?Math.ceil(next/2):0;
  const seconds=Math.ceil(baseSeconds*Math.pow(next,1.30));
  return{next,gold,seconds,resources:{[primary]:primaryAmount,[secondary]:secondaryAmount,...(essence?{essence}: {})}};
}
export function serverClockOffset(serverNow,clientNow=Date.now()){const n=Date.parse(serverNow||'');return Number.isFinite(n)?n-clientNow:0;}
export function remainingMs(finishesAt,offset=0,clientNow=Date.now()){const end=Date.parse(finishesAt||'');return Number.isFinite(end)?Math.max(0,end-(clientNow+offset)):0;}
export function formatDurationSeconds(total){let s=Math.max(0,Math.ceil(Number(total)||0));const h=Math.floor(s/3600);s%=3600;const m=Math.floor(s/60);s%=60;return h?`${h}h ${m}m`:m?`${m}m ${s}s`:`${s}s`;}
export function storageCap(warehouseLevel=1,fortressLevel=1){return 180+Math.max(1,Number(warehouseLevel))*120+Math.max(1,Number(fortressLevel))*20;}
export function offlineCapHours(warehouseLevel=1,fortressLevel=1){return Math.min(12,4+Math.max(1,Number(warehouseLevel))*2+Math.floor(Math.max(1,Number(fortressLevel))/2));}
export function missionTargets(memberCount=1){const m=Math.max(1,Number(memberCount)||1);return{combats:50+12*m,resources:800+210*m,crafts:20+9*m,bosses:10+Math.ceil(4.5*m)};}
