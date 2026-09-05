import { createClient } from 'npm:@supabase/supabase-js@2';

const SUPABASE_URL=Deno.env.get('SUPABASE_URL')??'';
const publishableKeys=JSON.parse(Deno.env.get('SUPABASE_PUBLISHABLE_KEYS')??'{}');
const secretKeys=JSON.parse(Deno.env.get('SUPABASE_SECRET_KEYS')??'{}');
const PUBLISHABLE_KEY=publishableKeys.default??Deno.env.get('SUPABASE_ANON_KEY')??'';
const SECRET_KEY=secretKeys.default??Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')??'';
const admin=createClient(SUPABASE_URL,SECRET_KEY,{auth:{persistSession:false,autoRefreshToken:false}});
const cors={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'authorization, x-client-info, apikey, content-type','Access-Control-Allow-Methods':'POST, OPTIONS'};
const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{...cors,'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
const APP_URL='https://nexus-realms-web3.onrender.com/';

async function authUser(req:Request){
  const h=req.headers.get('Authorization');
  if(!h)throw new Error('AUTH_REQUIRED');
  const scoped=createClient(SUPABASE_URL,PUBLISHABLE_KEY,{auth:{persistSession:false,autoRefreshToken:false},global:{headers:{Authorization:h}}});
  const token=h.replace(/^Bearer\s+/i,'');
  const {data:{user},error}=await scoped.auth.getUser(token);
  if(error||!user)throw new Error('AUTH_INVALID');
  return user;
}
async function characterFor(userId:string){
  const {data,error}=await admin.from('characters').select('id,name,level,created_at,founder_pack_owned,premium_credits_demo').eq('user_id',userId).eq('slot',1).single();
  if(error)throw error;
  return data;
}
async function stateFor(user:any,message?:string){
  const c=await characterFor(user.id);
  const {data:codeData,error:codeErr}=await admin.rpc('ensure_referral_profile',{p_character:c.id});
  if(codeErr)throw codeErr;
  const code=String(codeData||'');
  const [cfgRes,attrRes,invitesRes,rewardsRes]=await Promise.all([
    admin.from('referral_config').select('*').eq('id',1).single(),
    admin.from('referral_attributions').select('referrer_character_id,code_used,status,created_at,rewarded_at').eq('referred_character_id',c.id).maybeSingle(),
    admin.from('referral_attributions').select('referred_character_id,status,created_at,rewarded_at').eq('referrer_character_id',c.id).order('created_at',{ascending:false}).limit(25),
    admin.from('referral_rewards').select('referred_character_id,referrer_premium_credits,created_at').eq('referrer_character_id',c.id).order('created_at',{ascending:false}).limit(50)
  ]);
  for(const r of [cfgRes,attrRes,invitesRes,rewardsRes])if((r as any).error)throw (r as any).error;
  const cfg=cfgRes.data;
  let invitedBy:any=null;
  if(attrRes.data){
    const {data:rchar}=await admin.from('characters').select('name').eq('id',attrRes.data.referrer_character_id).maybeSingle();
    invitedBy={code:attrRes.data.code_used,status:attrRes.data.status,name:rchar?.name||'Adventurer',createdAt:attrRes.data.created_at,rewardedAt:attrRes.data.rewarded_at};
  }
  const inviteRows=invitesRes.data??[];
  const ids=inviteRows.map((x:any)=>x.referred_character_id);
  const names=new Map<string,string>();
  if(ids.length){
    const {data:chars,error}=await admin.from('characters').select('id,name').in('id',ids);
    if(error)throw error;
    for(const x of chars??[])names.set(String(x.id),String(x.name));
  }
  const rewardBy=new Map<string,number>();
  for(const r of rewardsRes.data??[])rewardBy.set(String(r.referred_character_id),Number(r.referrer_premium_credits||0));
  const referrals=inviteRows.map((x:any)=>({name:names.get(String(x.referred_character_id))||'Adventurer',status:x.status,createdAt:x.created_at,rewardedAt:x.rewarded_at,rewardCredits:rewardBy.get(String(x.referred_character_id))||0}));
  const rewarded=referrals.filter((x:any)=>x.status==='rewarded').length;
  const totalCredits=(rewardsRes.data??[]).reduce((n:number,x:any)=>n+Number(x.referrer_premium_credits||0),0);
  const deadline=new Date(new Date(c.created_at).getTime()+Number(cfg.attribution_window_days||7)*86400000).toISOString();
  return {ok:true,...(message?{message}:{}),mode:'ONE_LEVEL_NONCASH',character:{id:c.id,name:c.name,level:Number(c.level),founderPackOwned:Boolean(c.founder_pack_owned),premiumCreditsDemo:Number(c.premium_credits_demo||0)},profile:{code,shareUrl:`${APP_URL}?ref=${encodeURIComponent(code)}`},config:{active:Boolean(cfg.active),referrerPremiumCredits:Number(cfg.referrer_premium_credits),referredPremiumCredits:Number(cfg.referred_premium_credits),attributionWindowDays:Number(cfg.attribution_window_days)},attribution:{canAttach:!attrRes.data&&!c.founder_pack_owned&&Date.now()<new Date(deadline).getTime(),deadline,invitedBy},stats:{total:referrals.length,rewarded,totalPremiumCredits:totalCredits},referrals,disclaimer:{es:'Programa de un solo nivel. Las recompensas son Créditos Premium internos, no retirables y sin valor monetario. Solo se entregan cuando el referido compra y paga correctamente el Pack Fundador.',en:'Single-level program. Rewards are internal, non-withdrawable Premium Credits with no monetary value. Rewards are issued only after the referred player successfully pays for the Founder Pack.'}};
}
async function applyCode(user:any,codeRaw:string){
  const c=await characterFor(user.id);
  const code=String(codeRaw||'').trim().toUpperCase();
  if(!/^[A-Z0-9]{6,20}$/.test(code))throw new Error('Invalid referral code');
  const {data:existing,error:eErr}=await admin.from('referral_attributions').select('code_used,status').eq('referred_character_id',c.id).maybeSingle();
  if(eErr)throw eErr;
  if(existing)return stateFor(user,'Referral already attached');
  const {error}=await admin.rpc('apply_referral_code',{p_referred:c.id,p_code:code});
  if(error)throw error;
  return stateFor(user,'Referral attached');
}

Deno.serve(async(req:Request)=>{
  if(req.method==='OPTIONS')return new Response('ok',{headers:cors});
  if(req.method!=='POST')return json({error:'method_not_allowed'},405);
  try{
    const user=await authUser(req);
    const input=await req.json().catch(()=>({}));
    const op=String(input?.op??'state');
    if(op==='state')return json(await stateFor(user));
    if(op==='action'&&String(input?.action||'')==='applyCode')return json(await applyCode(user,String(input?.payload?.code||'')));
    return json({error:'unknown_operation'},400);
  }catch(e){
    const message=e instanceof Error?e.message:'request_failed';
    return json({error:message},message==='AUTH_REQUIRED'||message==='AUTH_INVALID'?401:400);
  }
});
