import { createClient } from 'npm:@supabase/supabase-js@2';

const SUPABASE_URL=Deno.env.get('SUPABASE_URL')??'';
const publishableKeys=JSON.parse(Deno.env.get('SUPABASE_PUBLISHABLE_KEYS')??'{}');
const secretKeys=JSON.parse(Deno.env.get('SUPABASE_SECRET_KEYS')??'{}');
const PUBLISHABLE_KEY=publishableKeys.default??Deno.env.get('SUPABASE_ANON_KEY')??'';
const SECRET_KEY=secretKeys.default??Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')??'';
const admin=createClient(SUPABASE_URL,SECRET_KEY,{auth:{persistSession:false,autoRefreshToken:false}});
const cors={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'authorization, x-client-info, apikey, content-type','Access-Control-Allow-Methods':'POST, OPTIONS'};
const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{...cors,'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});

async function authUser(req:Request){const h=req.headers.get('Authorization');if(!h)throw new Error('AUTH_REQUIRED');const scoped=createClient(SUPABASE_URL,PUBLISHABLE_KEY,{auth:{persistSession:false,autoRefreshToken:false},global:{headers:{Authorization:h}}});const {data:{user},error}=await scoped.auth.getUser(h.replace(/^Bearer\s+/i,''));if(error||!user)throw new Error('AUTH_INVALID');return user;}
async function characterFor(userId:string){const {data,error}=await admin.from('characters').select('*').eq('user_id',userId).eq('slot',1).single();if(error)throw error;return data;}
async function buildProfile(characterId:string,pvp=false){const {data,error}=await admin.rpc('phase3_build_profile',{p_character:characterId,p_pvp:pvp});if(error)throw error;return data;}
async function state(user:any){const c=await characterFor(user.id);const {data:classSpecs,error:classErr}=await admin.from('phase3_specializations').select('id').eq('class_key',c.class);if(classErr)throw classErr;const specIds=(classSpecs??[]).map((x:any)=>x.id);const [{data:sets,error:sErr},{data:specs,error:spErr},{data:skills,error:skErr},{data:eq,error:eqErr},{data:items,error:iErr},build]=await Promise.all([
 admin.from('phase3_set_definitions').select('*').order('class_key',{ascending:true}).order('id'),
 admin.from('phase3_specializations').select('*').eq('class_key',c.class).order('id'),
 specIds.length?admin.from('phase3_specialization_skills').select('*').in('specialization_id',specIds).order('min_level').order('id'):Promise.resolve({data:[],error:null}),
 admin.from('equipment').select('*').eq('character_id',c.id).maybeSingle(),
 admin.from('item_instances').select('id,custom_name,definition_id,rarity,atk,def,enhancement_level,set_id,metadata,item_definitions(name,type,slot)').eq('owner_character_id',c.id),
 buildProfile(c.id,false)
]);
 for(const e of [sErr,spErr,skErr,eqErr,iErr])if(e)throw e;
 const bySpec:Record<string,any[]>={};for(const sk of skills??[]){(bySpec[sk.specialization_id]??=[]).push({id:sk.id,name:sk.name,nameEs:sk.name_es,kind:sk.kind,manaCost:Number(sk.mana_cost),multiplier:Number(sk.multiplier),cooldownTurns:Number(sk.cooldown_turns),minLevel:Number(sk.min_level),metadata:sk.metadata??{}})}
 const setMap=new Map((sets??[]).map((s:any)=>[s.id,s]));
 const inventory=(items??[]).map((r:any)=>{const d=r.item_definitions??{},set:any=setMap.get(r.set_id);return{id:r.id,name:r.custom_name||d.name||'Unknown Item',slot:d.slot||r.metadata?.slot||null,rarity:r.rarity,atk:Number(r.atk??0),def:Number(r.def??0),enhancementLevel:Number(r.enhancement_level??0),setId:r.set_id??null,set:set?{id:set.id,name:set.name_en,nameEs:set.name_es,classKey:set.class_key,bonuses:{two:set.bonus_2,four:set.bonus_4,six:set.bonus_6}}:null}});
 const equip={weapon:eq?.weapon_item_id??null,helmet:eq?.helmet_item_id??null,armor:eq?.armor_item_id??null,gloves:eq?.gloves_item_id??null,boots:eq?.boots_item_id??null,ring:eq?.ring_item_id??null};
 const specsOut=(specs??[]).map((s:any)=>({id:s.id,name:s.name_en,nameEs:s.name_es,description:s.description_en,descriptionEs:s.description_es,unlockLevel:Number(s.unlock_level),statModifiers:s.stat_modifiers,passiveEffects:s.passive_effects,aiPriority:s.ai_priority,recommendedSetId:s.recommended_set_id,skills:bySpec[s.id]??[]}));
 return{ok:true,character:{id:c.id,name:c.name,class:c.class,level:Number(c.level),gold:Number(c.gold),specialization:c.specialization??null,respecCount:Number(c.specialization_respec_count??0)},equipment:equip,inventory,sets:(sets??[]).map((s:any)=>({id:s.id,name:s.name_en,nameEs:s.name_es,classKey:s.class_key,theme:s.theme,bonus2:s.bonus_2,bonus4:s.bonus_4,bonus6:s.bonus_6,recommendedSpecializations:s.recommended_specializations??[]})),specializations:specsOut,build};}
async function chooseSpecialization(user:any,payload:any){const c=await characterFor(user.id),id=String(payload?.id??'');const {data,error}=await admin.rpc('phase3_set_specialization',{p_character:c.id,p_specialization:id});if(error)throw error;return{ok:true,result:data,state:await state(user)}}
async function equip(user:any,payload:any){const c=await characterFor(user.id),id=String(payload?.itemId??'');const {data,error}=await admin.rpc('phase3_equip_item',{p_character:c.id,p_item:id});if(error)throw error;return{ok:true,result:data,state:await state(user)}}
async function unequip(user:any,payload:any){const c=await characterFor(user.id),slot=String(payload?.slot??'');const {data,error}=await admin.rpc('phase3_unequip_slot',{p_character:c.id,p_slot:slot});if(error)throw error;return{ok:true,result:data,state:await state(user)}}

Deno.serve(async(req:Request)=>{if(req.method==='OPTIONS')return new Response('ok',{headers:cors});if(req.method!=='POST')return json({error:'method_not_allowed'},405);try{const user=await authUser(req),body=await req.json().catch(()=>({})),op=String(body?.op??'state');if(op==='state')return json(await state(user));if(op==='specialize')return json(await chooseSpecialization(user,body?.payload??{}));if(op==='equip')return json(await equip(user,body?.payload??{}));if(op==='unequip')return json(await unequip(user,body?.payload??{}));return json({error:'unknown_operation'},400)}catch(e){const m=e instanceof Error?e.message:'request_failed';const status=m==='AUTH_REQUIRED'||m==='AUTH_INVALID'?401:m.includes('locked')||m.includes('required')?403:400;return json({error:m},status)}});
