import { createClient } from 'npm:@supabase/supabase-js@2';

const SUPABASE_URL=Deno.env.get('SUPABASE_URL')??'';
const publishableKeys=JSON.parse(Deno.env.get('SUPABASE_PUBLISHABLE_KEYS')??'{}');
const secretKeys=JSON.parse(Deno.env.get('SUPABASE_SECRET_KEYS')??'{}');
const PUBLISHABLE_KEY=publishableKeys.default??Deno.env.get('SUPABASE_ANON_KEY')??'';
const SECRET_KEY=secretKeys.default??Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')??'';
const admin=createClient(SUPABASE_URL,SECRET_KEY,{auth:{persistSession:false,autoRefreshToken:false}});
const cors={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'authorization, x-client-info, apikey, content-type','Access-Control-Allow-Methods':'POST, OPTIONS'};
const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{...cors,'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
const weekStart=()=>{const d=new Date();const day=(d.getUTCDay()+6)%7;return new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate()-day)).toISOString().slice(0,10)};

async function authUser(req:Request){const h=req.headers.get('Authorization');if(!h)throw new Error('AUTH_REQUIRED');const scoped=createClient(SUPABASE_URL,PUBLISHABLE_KEY,{auth:{persistSession:false,autoRefreshToken:false},global:{headers:{Authorization:h}}});const {data:{user},error}=await scoped.auth.getUser(h.replace(/^Bearer\s+/i,''));if(error||!user)throw new Error('AUTH_INVALID');return user;}
async function characterFor(userId:string){const {data,error}=await admin.from('characters').select('id,name,class,level,gold,renown,energy,max_energy,hp,max_hp,mana,max_mana,regen_boost_until').eq('user_id',userId).eq('slot',1).single();if(error)throw error;return data;}
function quote(d:any,level:number){const next=Math.max(2,Number(level||1)+1),gold=Math.ceil(Number(d.base_gold)*Math.pow(next,1.55)),primaryAmount=Math.ceil((8+Number(d.base_gold)/70)*next),secondaryAmount=Math.ceil(4*next),essence=['fortress','laboratory','altar'].includes(d.building_key)&&next>=4?Math.ceil(next/2):0,seconds=Math.ceil(Number(d.base_seconds)*Math.pow(next,1.30));return{next,gold,seconds,resources:{[d.primary_resource]:primaryAmount,[d.secondary_resource]:secondaryAmount,...(essence?{essence}:{})}};}
function targets(n:number){const m=Math.max(1,n);return{combats:50+12*m,resources:800+210*m,crafts:20+9*m,bosses:10+Math.ceil(4.5*m)};}
async function rpc(name:string,args:any){const {data,error}=await admin.rpc(name,args);if(error)throw error;return data;}

async function bastionState(c:any){await rpc('phase4_settle_bastion',{p_character:c.id});const [defsRes,buildRes,stockRes,buffsRes,resRes,charRes]=await Promise.all([
 admin.from('bastion_building_defs').select('*').order('building_key'),
 admin.from('bastion_buildings').select('*').eq('character_id',c.id).order('building_key'),
 admin.from('bastion_stockpile').select('*').eq('character_id',c.id).order('resource_key'),
 admin.from('bastion_buffs').select('*').eq('character_id',c.id).gt('expires_at',new Date().toISOString()),
 admin.from('resources').select('resource_key,amount').eq('character_id',c.id),
 admin.from('characters').select('gold,regen_boost_until').eq('id',c.id).single()
]);for(const r of [defsRes,buildRes,stockRes,buffsRes,resRes,charRes])if((r as any).error)throw (r as any).error;
 const defs=defsRes.data??[],buildings=buildRes.data??[],byLevel=new Map(buildings.map((b:any)=>[b.building_key,Number(b.level)]));
 const storageCap=180+(byLevel.get('warehouse')??1)*120+(byLevel.get('fortress')??1)*20;
 const offlineCapHours=Math.min(12,4+(byLevel.get('warehouse')??1)*2+Math.floor((byLevel.get('fortress')??1)/2));
 const resources:Record<string,number>={ore:0,wood:0,fish:0,essence:0};for(const r of resRes.data??[])resources[r.resource_key]=Number(r.amount);
 const stockpile:Record<string,number>={ore:0,wood:0,fish:0,essence:0};for(const r of stockRes.data??[])stockpile[r.resource_key]=Number(r.amount);
 const defMap=new Map(defs.map((d:any)=>[d.building_key,d]));
 return{storageCap,offlineCapHours,stockpile,resources,gold:Number(charRes.data?.gold??0),regenBoostUntil:charRes.data?.regen_boost_until??null,buffs:buffsRes.data??[],buildings:buildings.map((b:any)=>{const d:any=defMap.get(b.building_key)||{};return{...b,definition:d,quote:quote(d,Number(b.level))}})};
}

async function clanState(c:any){const {data:me,error}=await admin.from('guild_members').select('*').eq('character_id',c.id).maybeSingle();if(error)throw error;if(!me)return null;const guildId=me.guild_id,week=weekStart();await rpc('ensure_guild_week',{p_guild_id:guildId});await rpc('phase4_ensure_clan_week',{p_guild:guildId});const warId=await rpc('phase4_ensure_war',{p_guild:guildId});
 const [guildRes,membersRes,treasuryRes,researchDefsRes,researchRes,buffsRes,missionRes,claimRes,raidRes,raidRanksRes,shopRes,purchasesRes,auditRes,warRes]=await Promise.all([
  admin.from('guilds').select('*').eq('id',guildId).single(),admin.from('guild_members').select('*').eq('guild_id',guildId).order('role'),admin.from('guild_treasury_resources').select('*').eq('guild_id',guildId).order('resource_key'),admin.from('guild_research_definitions').select('*').order('research_key'),admin.from('guild_research').select('*').eq('guild_id',guildId).order('research_key'),admin.from('guild_buffs').select('*').eq('guild_id',guildId).gt('expires_at',new Date().toISOString()),admin.from('guild_mission_progress').select('*').eq('guild_id',guildId).eq('week_start',week).single(),admin.from('guild_mission_claims').select('claimed_at').eq('guild_id',guildId).eq('character_id',c.id).eq('week_start',week).maybeSingle(),admin.from('guild_raids').select('*').eq('guild_id',guildId).eq('week_start',week).maybeSingle(),admin.from('guild_raid_contributions').select('*').eq('guild_id',guildId).eq('week_start',week).order('damage',{ascending:false}),admin.from('guild_shop_items').select('*').eq('enabled',true).order('cost_credits'),admin.from('guild_shop_purchases').select('item_key,cost_credits,created_at').eq('guild_id',guildId).eq('character_id',c.id).eq('week_start',week),admin.from('guild_audit_log').select('*').eq('guild_id',guildId).order('created_at',{ascending:false}).limit(30),warId?admin.from('guild_wars').select('*').eq('id',warId).maybeSingle():Promise.resolve({data:null,error:null})
 ]);for(const r of [guildRes,membersRes,treasuryRes,researchDefsRes,researchRes,buffsRes,missionRes,claimRes,raidRes,raidRanksRes,shopRes,purchasesRes,auditRes,warRes])if((r as any).error)throw (r as any).error;
 const memberRows=membersRes.data??[],ids=memberRows.map((x:any)=>x.character_id);let chars:any[]=[];if(ids.length){const q=await admin.from('characters').select('id,name,class,level,renown').in('id',ids);if(q.error)throw q.error;chars=q.data??[];}const charMap=new Map(chars.map((x:any)=>[x.id,x]));const members=memberRows.map((x:any)=>({...x,character:charMap.get(x.character_id)??null}));
 const rankRows=raidRanksRes.data??[],rankIds=rankRows.map((x:any)=>x.character_id),rankNames=new Map(members.map((x:any)=>[x.character_id,x.character?.name??'Adventurer']));const bossRanking=rankRows.map((x:any,i:number)=>({rank:i+1,characterId:x.character_id,name:rankNames.get(x.character_id)??'Adventurer',damage:Number(x.damage),attempts:Number(x.attempts),claimed:Boolean(x.claimed_at)}));
 const treasury:Record<string,number>={gold:Number(guildRes.data?.treasury_demo??0),ore:0,wood:0,fish:0,essence:0};for(const r of treasuryRes.data??[])treasury[r.resource_key]=Number(r.amount);
 const researchLevels=new Map((researchRes.data??[]).map((r:any)=>[r.research_key,Number(r.level)]));const research=(researchDefsRes.data??[]).map((d:any)=>{const level=researchLevels.get(d.research_key)??0,next=level+1;return{...d,level,nextCost:level>=Number(d.max_level)?null:{gold:Math.ceil(Number(d.cost_gold_base)*Math.pow(next,1.45)),resource:d.cost_resource,amount:Number(d.cost_resource_base)*next}}});
 const t=targets(members.length),p=missionRes.data||{combats:0,resources:0,crafts:0,bosses:0};const ready=Number(p.combats)>=t.combats&&Number(p.resources)>=t.resources&&Number(p.crafts)>=t.crafts&&Number(p.bosses)>=t.bosses;
 const purchaseCounts:Record<string,number>={};for(const x of purchasesRes.data??[])purchaseCounts[x.item_key]=(purchaseCounts[x.item_key]??0)+1;const shop=(shopRes.data??[]).map((x:any)=>({...x,purchasedThisWeek:purchaseCounts[x.item_key]??0}));
 let war:any=null;if(warRes.data){const w=warRes.data,opponentId=w.guild_a===guildId?w.guild_b:w.guild_a;const {data:op}=await admin.from('guilds').select('id,name,tag,level').eq('id',opponentId).maybeSingle();war={...w,ourScore:Number(w.guild_a===guildId?w.score_a:w.score_b),opponentScore:Number(w.guild_a===guildId?w.score_b:w.score_a),opponent:op??null};}
 return{clan:guildRes.data,membership:me,members,treasury,research,buffs:buffsRes.data??[],mission:{weekStart:week,progress:{combats:Number(p.combats),resources:Number(p.resources),crafts:Number(p.crafts),bosses:Number(p.bosses)},targets:t,ready,claimed:Boolean(claimRes.data),collectiveRewardGranted:Boolean(p.collective_reward_granted_at)},raid:raidRes.data?{...raidRes.data,max_hp:Number(raidRes.data.max_hp),current_hp:Number(raidRes.data.current_hp)}:null,bossRanking,shop,shopCredits:Number(me.shop_credits??0),audit:auditRes.data??[],war};
}

async function stateFor(user:any,message?:string){const c=await characterFor(user.id);const [bastion,clan2]=await Promise.all([bastionState(c),clanState(c)]);return{ok:true,serverNow:new Date().toISOString(),...(message?{message}:{}),character:{id:c.id,name:c.name,class:c.class,level:Number(c.level)},bastion,clan2};}
async function action(user:any,name:string,payload:any){const c=await characterFor(user.id);let message='OK';
 if(name==='bastionUpgrade'){await rpc('phase4_bastion_upgrade',{p_character:c.id,p_building:String(payload?.buildingKey??'')});message='Mejora iniciada';}
 else if(name==='bastionClaim'){await rpc('phase4_bastion_claim',{p_character:c.id});message='Producción recogida';}
 else if(name==='bastionAltar'){await rpc('phase4_activate_altar',{p_character:c.id});message='Buff del Altar activado';}
 else if(name==='clanDonate'){await rpc('phase4_clan_donate',{p_character:c.id,p_gold:Number(payload?.gold??0),p_resource:payload?.resource?String(payload.resource):null,p_amount:Number(payload?.amount??0)});message='Donación registrada';}
 else if(name==='clanResearch'){await rpc('phase4_clan_research',{p_character:c.id,p_research:String(payload?.researchKey??'')});message='Investigación mejorada';}
 else if(name==='clanBuff'){await rpc('phase4_clan_activate_buff',{p_character:c.id,p_buff:String(payload?.buffKey??'')});message='Buff de clan activado';}
 else if(name==='clanMissionClaim'){await rpc('phase4_clan_claim_mission',{p_character:c.id});message='Recompensa de misión reclamada';}
 else if(name==='clanShopBuy'){await rpc('phase4_clan_shop_buy',{p_character:c.id,p_item:String(payload?.itemKey??'')});message='Compra de clan completada';}
 else if(name==='clanSetRole'){await rpc('clan_set_role',{p_character_id:c.id,p_target_character_id:String(payload?.characterId??''),p_role:String(payload?.role??'member')});message='Rol actualizado';}
 else if(name==='clanKick'){await rpc('clan_kick',{p_character_id:c.id,p_target_character_id:String(payload?.characterId??'')});message='Miembro expulsado';}
 else if(name==='clanTransfer'){await rpc('clan_transfer_leadership',{p_character_id:c.id,p_target_character_id:String(payload?.characterId??'')});message='Liderazgo transferido';}
 else throw new Error('Unknown Phase 4 action');
 return stateFor(user,message);
}

Deno.serve(async(req:Request)=>{if(req.method==='OPTIONS')return new Response('ok',{headers:cors});if(req.method!=='POST')return json({error:'method_not_allowed'},405);try{const user=await authUser(req),body=await req.json().catch(()=>({})),op=String(body?.op??'state');if(op==='state')return json(await stateFor(user));if(op==='action')return json(await action(user,String(body?.action??''),body?.payload??{}));return json({error:'unknown_operation'},400)}catch(e){const m=e instanceof Error?e.message:'request_failed';const status=m==='AUTH_REQUIRED'||m==='AUTH_INVALID'?401:m.includes('permission')?403:400;return json({error:m},status)}});
