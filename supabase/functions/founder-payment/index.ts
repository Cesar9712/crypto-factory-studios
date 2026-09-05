import { createClient } from 'npm:@supabase/supabase-js@2';

const SUPABASE_URL=Deno.env.get('SUPABASE_URL')??'';
const publishableKeys=JSON.parse(Deno.env.get('SUPABASE_PUBLISHABLE_KEYS')??'{}');
const secretKeys=JSON.parse(Deno.env.get('SUPABASE_SECRET_KEYS')??'{}');
const PUBLISHABLE_KEY=publishableKeys.default??Deno.env.get('SUPABASE_ANON_KEY')??'';
const SECRET_KEY=secretKeys.default??Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')??'';
const admin=createClient(SUPABASE_URL,SECRET_KEY,{auth:{persistSession:false,autoRefreshToken:false}});
const cors={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'authorization, x-client-info, apikey, content-type','Access-Control-Allow-Methods':'POST, OPTIONS'};
const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{...cors,'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});

const BSC_RPCS=['https://bsc-dataseed.binance.org/','https://bsc-rpc.publicnode.com'];
const RPC_TIMEOUT_MS=7000;
const TRANSFER_TOPIC='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
const norm=(x:unknown)=>String(x??'').toLowerCase();
const toBigInt=(x:unknown)=>{try{return BigInt(String(x??'0x0'))}catch{return 0n}};
const topicAddress=(x:unknown)=>('0x'+String(x??'').replace(/^0x/,'').slice(-40)).toLowerCase();

async function authUser(req:Request){
  const h=req.headers.get('Authorization');
  if(!h)throw new Error('AUTH_REQUIRED');
  const scoped=createClient(SUPABASE_URL,PUBLISHABLE_KEY,{auth:{persistSession:false,autoRefreshToken:false},global:{headers:{Authorization:h}}});
  const token=h.replace(/^Bearer\s+/i,'');
  const {data:{user},error}=await scoped.auth.getUser(token);
  if(error||!user)throw new Error('AUTH_INVALID');
  return user;
}

async function rpc(method:string,params:unknown[]){
  let last:unknown=null;
  for(const url of BSC_RPCS){
    try{
      const r=await fetch(url,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:1,method,params}),signal:AbortSignal.timeout(RPC_TIMEOUT_MS)});
      const j=await r.json();
      if(r.ok&&!j.error)return j.result;
      last=j.error??r.status;
    }catch(e){last=e}
  }
  console.error('BSC RPC failure',method,last instanceof Error?last.name:String(last));
  throw new Error('BSC RPC unavailable');
}

async function verifyPayment(txHash:string,payment:any,priceUsdCents:number){
  const hash=String(txHash||'').trim().toLowerCase();
  if(!/^0x[0-9a-f]{64}$/.test(hash))throw new Error('Invalid transaction hash');
  const expectedChain=BigInt(Number(payment?.chain_id||56));
  if(toBigInt(await rpc('eth_chainId',[]))!==expectedChain)throw new Error('Wrong payment network');
  const receipt=await rpc('eth_getTransactionReceipt',[hash]);
  if(!receipt)throw new Error('Transaction not found yet');
  if(norm(receipt.status)!=='0x1')throw new Error('Transaction failed');
  if(!receipt.blockNumber)throw new Error('Transaction is still pending');
  const latest=toBigInt(await rpc('eth_blockNumber',[]));
  const mined=toBigInt(receipt.blockNumber);
  const confirmations=Number(latest>=mined?latest-mined+1n:0n);
  const minConfirmations=Math.max(1,Number(payment?.min_confirmations||3));
  if(confirmations<minConfirmations)throw new Error(`Payment needs ${minConfirmations} confirmations (${confirmations}/${minConfirmations})`);
  const token=norm(payment?.token_contract),recipient=norm(payment?.recipient);
  if(!/^0x[0-9a-f]{40}$/.test(token)||!/^0x[0-9a-f]{40}$/.test(recipient))throw new Error('Payment configuration invalid');
  let received=0n;
  for(const log of receipt.logs??[]){
    if(norm(log?.address)!==token)continue;
    if(norm(log?.topics?.[0])!==TRANSFER_TOPIC)continue;
    if(topicAddress(log?.topics?.[2])!==recipient)continue;
    received+=toBigInt(log?.data);
  }
  const decimals=Math.max(0,Number(payment?.decimals||18));
  const required=BigInt(Math.round(priceUsdCents))*10n**BigInt(decimals)/100n;
  if(received<required)throw new Error('Payment amount or recipient does not match');
  return{hash,receivedRaw:received.toString(),requiredRaw:required.toString(),confirmations};
}

Deno.serve(async(req:Request)=>{
  if(req.method==='OPTIONS')return new Response('ok',{headers:cors});
  if(req.method!=='POST')return json({error:'method_not_allowed'},405);
  try{
    const user=await authUser(req);
    const input=await req.json().catch(()=>({}));
    const txHash=String(input?.txHash||'').trim().toLowerCase();
    if(!/^0x[0-9a-f]{64}$/.test(txHash))throw new Error('Invalid transaction hash');
    const packKey=String(input?.packKey||'rift_founder');
    const {data:character,error:cErr}=await admin.from('characters').select('id,name,founder_pack_owned').eq('user_id',user.id).eq('slot',1).single();
    if(cErr)throw cErr;
    if(character.founder_pack_owned)return json({ok:true,alreadyOwned:true,message:'Pack Fundador ya adquirido'});
    const {data:pack,error:pErr}=await admin.from('founder_pack_config').select('*').eq('pack_key',packKey).eq('active',true).maybeSingle();
    if(pErr)throw pErr;
    if(!pack)throw new Error('Founder pack not found');
    if(!pack.checkout_enabled)throw new Error('Founder checkout is disabled');
    let {data:order,error:oErr}=await admin.from('founder_pack_orders').select('*').eq('character_id',character.id).eq('pack_key',pack.pack_key).maybeSingle();
    if(oErr)throw oErr;
    if(order?.status==='paid')return json({ok:true,alreadyOwned:true,message:'Pack Fundador ya adquirido'});
    if(!order){
      const {data:newOrder,error:nErr}=await admin.from('founder_pack_orders').insert({character_id:character.id,pack_key:pack.pack_key,status:'awaiting_payment',price_usd_cents:Number(pack.price_usd_cents),payment_network:pack.payment_config?.network||'BNB Smart Chain',payment_asset:`${pack.payment_config?.asset||'USDT'} ${pack.payment_config?.standard||'BEP20'}`}).select('*').single();
      if(nErr)throw nErr;
      order=newOrder;
    }
    const {data:used,error:uErr}=await admin.from('founder_pack_orders').select('id').eq('payment_reference',txHash).neq('id',order.id).maybeSingle();
    if(uErr)throw uErr;
    if(used)throw new Error('Transaction hash already used');
    const verified=await verifyPayment(txHash,pack.payment_config||{},Number(pack.price_usd_cents));
    const {error:updateErr}=await admin.from('founder_pack_orders').update({status:'awaiting_payment',payment_network:pack.payment_config?.network||'BNB Smart Chain',payment_asset:`${pack.payment_config?.asset||'USDT'} ${pack.payment_config?.standard||'BEP20'}`,payment_reference:verified.hash,payment_amount_raw:verified.receivedRaw,payment_confirmations:verified.confirmations,verified_at:new Date().toISOString()}).eq('id',order.id);
    if(updateErr)throw updateErr;
    const {error:fulfillErr}=await admin.rpc('fulfill_founder_pack',{p_order:order.id,p_payment_reference:verified.hash});
    if(fulfillErr)throw fulfillErr;
    return json({ok:true,message:'Pago verificado. Pack Fundador activado.',txHash:verified.hash,confirmations:verified.confirmations});
  }catch(e){
    const message=e instanceof Error?e.message:'request_failed';
    return json({error:message},message==='AUTH_REQUIRED'||message==='AUTH_INVALID'?401:400);
  }
});
