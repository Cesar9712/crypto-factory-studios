from __future__ import annotations
import json, os, re, sqlite3, uuid
from contextvars import ContextVar
from typing import Any
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from .config import Settings
from .db_runtime import DB
from .storage import StorageService
from .security import hash_password, verify_password, new_token, token_hash, now, sha256_bytes
from .upload_security import UploadSecurityService
from .payments import PaymentMethodRegistry, PriceService, MockBlockchainVerifier, payment_fingerprint, canonical_txid
from .blockchain import ProductionBlockchainVerifier
from .routes_v03 import register_routes
from .routes_platform import register_platform_routes
from .routes_game_edit import register_game_edit_routes
from .routes_payment_extras import register_payment_extra_routes
from .routes_tropipay import register_tropipay_routes
from .routes_bitshelf import register_bitshelf_routes
from .routes_prompt_factory import register_prompt_factory_routes

settings=Settings(); db=DB(settings.database_path, settings.database_url); storage=StorageService(settings)
payment_methods=PaymentMethodRegistry(settings); price_service=PriceService(settings)
payment_verifier=ProductionBlockchainVerifier(settings) if settings.payments_mode=='PRODUCTION' else MockBlockchainVerifier()
for _pm in payment_methods.values():
    db.execute('INSERT OR REPLACE INTO payment_methods(method_id,asset,network,standard,address,token_contract,enabled,production_allowed,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(_pm.method_id,_pm.asset,_pm.network,_pm.standard,_pm.address,_pm.token_contract,1 if _pm.enabled else 0,1 if _pm.production_allowed else 0,now()))
scanner=UploadSecurityService(settings.max_upload_bytes,settings.max_uncompressed_bytes,settings.max_archive_files,settings.max_compression_ratio,settings.antivirus_required)
app=FastAPI(title='Crypto Factory Studios API',version='0.7.0')
app.add_middleware(CORSMiddleware,allow_origins=list(settings.allowed_origins),allow_credentials=True,allow_methods=['GET','POST','PUT','DELETE'],allow_headers=['Authorization','Content-Type','X-Owner-Bootstrap','X-CSRF-Token'])
RATE:dict[str,list[int]]={}; REQUEST_SESSION:ContextVar[str|None]=ContextVar('cfs_request_session',default=None)

PLAY_CSP=(
    "sandbox allow-scripts allow-forms allow-modals allow-pointer-lock allow-popups allow-downloads; "
    "default-src 'self' data: blob:; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; media-src 'self' data: blob:; font-src 'self' data:; "
    "connect-src https: wss:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
)

def rid()->str: return 'req_'+uuid.uuid4().hex[:16]
def fail(code:str,msg:str,status:int=400): raise HTTPException(status,detail={'error_code':code,'message':msg,'request_id':rid()})
def limited(key:str,limit:int,window:int=60):
    t=now(); xs=[v for v in RATE.get(key,[]) if t-v<window]
    if len(xs)>=limit: fail('rate_limited','Try again later',429)
    xs.append(t); RATE[key]=xs

def audit(actor:str|None,action:str,target_type:str,target_id:str|None=None,details:dict|None=None): db.execute('INSERT INTO audit_logs(actor_id,action,target_type,target_id,details_json,created_at) VALUES(?,?,?,?,?,?)',(actor,action,target_type,target_id,json.dumps(details or {},separators=(',',':')),now()))
def session_user(authorization:str|None):
    raw=authorization[7:] if authorization and authorization.startswith('Bearer ') else REQUEST_SESSION.get()
    if not raw: fail('auth_required','Authentication required',401)
    s=db.one('SELECT * FROM sessions WHERE token_hash=? AND revoked_at=0 AND expires_at>?',(token_hash(raw),now()))
    if not s: fail('invalid_session','Session expired or invalid',401)
    u=db.one('SELECT id,email,display_name,role,created_at FROM users WHERE id=? AND disabled=0',(s['user_id'],))
    if not u: fail('invalid_session','Account unavailable',401)
    return u,raw

def creator_profile(user_id:str): return db.one('SELECT * FROM creator_profiles WHERE user_id=?',(user_id,))
def effective_plan(user_id:str):
    cp=creator_profile(user_id)
    if not cp:return None
    plan=db.one('SELECT * FROM creator_plans WHERE plan_id=? AND active=1',(cp['plan_id'],))
    return {**cp,'limits':plan} if plan else cp

def slugify(s:str)->str: return (re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')[:60] or 'game')
class RegisterIn(BaseModel): email:EmailStr; password:str=Field(min_length=10,max_length=128); display_name:str=Field(min_length=2,max_length=32)
class LoginIn(BaseModel): email:EmailStr; password:str

@app.middleware('http')
async def headers(request:Request,call_next):
    cookie_token=request.cookies.get('cfs_session'); marker=REQUEST_SESSION.set(cookie_token)
    try:
        csrf_exempt=request.url.path in {'/api/v1/auth/register','/api/v1/auth/login'}
        if request.method not in {'GET','HEAD','OPTIONS'} and cookie_token and not request.headers.get('Authorization') and not csrf_exempt:
            if not request.cookies.get('cfs_csrf') or request.cookies.get('cfs_csrf')!=request.headers.get('X-CSRF-Token'):
                return JSONResponse(status_code=403,content={'detail':{'error_code':'csrf_failed','message':'CSRF validation failed','request_id':rid()}})
        response=await call_next(request)
    finally: REQUEST_SESSION.reset(marker)
    play=request.url.path.startswith('/play/')
    security_headers={
        'X-Content-Type-Options':'nosniff',
        'Referrer-Policy':'strict-origin-when-cross-origin',
        'Permissions-Policy':'camera=(), microphone=(), geolocation=()',
        'X-Frame-Options':'DENY',
        'Cross-Origin-Resource-Policy':'cross-origin' if play else 'same-origin',
        'X-Request-ID':request.headers.get('X-Request-ID') or rid(),
    }
    if play: security_headers['Content-Security-Policy']=PLAY_CSP
    response.headers.update(security_headers)
    return response

@app.get('/health')
def health(): return {'ok':True,'service':'crypto-factory-studios','version':'0.7.0','git_commit':os.getenv('RENDER_GIT_COMMIT','')}
@app.get('/ready')
def ready():
    db_ok=db.ping(); storage_ok=storage.ping()
    provider_status=payment_verifier.status() if settings.payments_mode=='PRODUCTION' else {}
    payments_ready=(all(provider_status.get(m.method_id,False) for m in payment_methods.values() if m.enabled and m.production_allowed) if settings.payments_mode=='PRODUCTION' else True)
    payload={'ready':bool(db_ok and storage_ok),'environment':settings.environment,'payments_mode':settings.payments_mode,'payments_ready':payments_ready,'upload_scan_engine':'external-required' if settings.antivirus_required else 'built-in-static','external_antivirus_required':settings.antivirus_required,'database_backend':db.backend,'database_persistent':db.persistent,'storage_backend':settings.storage_backend}
    if not payload['ready']: raise HTTPException(503,detail=payload)
    return payload

@app.post('/api/v1/auth/register')
def register(body:RegisterIn,request:Request):
    limited('register:'+request.client.host,500 if settings.environment in {'development','test'} else 12); uid='usr_'+uuid.uuid4().hex; t=now()
    try: db.execute('INSERT INTO users(id,email,password_hash,display_name,role,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(uid,body.email.lower().strip(),hash_password(body.password),body.display_name.strip(),'player',t,t))
    except sqlite3.IntegrityError: fail('account_exists','Account already exists',409)
    audit(uid,'account_created','user',uid); return make_session(uid)
def make_session(uid:str):
    token=new_token(); csrf=new_token(); t=now(); db.execute('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)',(token_hash(token),uid,t,t+settings.session_seconds))
    payload={'expires_in':settings.session_seconds,'user':db.one('SELECT id,email,display_name,role,created_at FROM users WHERE id=?',(uid,))}
    if settings.environment!='production': payload['access_token']=token
    response=JSONResponse(payload); secure=settings.environment=='production'; response.set_cookie('cfs_session',token,max_age=settings.session_seconds,httponly=True,secure=secure,samesite='strict',path='/'); response.set_cookie('cfs_csrf',csrf,max_age=settings.session_seconds,httponly=False,secure=secure,samesite='strict',path='/'); return response
@app.post('/api/v1/auth/login')
def login(body:LoginIn,request:Request):
    limited('login:'+request.client.host,500 if settings.environment in {'development','test'} else 10); u=db.one('SELECT * FROM users WHERE email=? COLLATE NOCASE',(body.email.lower().strip(),))
    if not u or not verify_password(body.password,u['password_hash']): fail('invalid_credentials','Invalid email or password',401)
    if u.get('disabled',0): fail('account_disabled','Account unavailable',403)
    audit(u['id'],'login','user',u['id']); return make_session(u['id'])
@app.post('/api/v1/auth/logout')
def logout(authorization:str|None=Header(default=None)):
    user,raw=session_user(authorization); db.execute('UPDATE sessions SET revoked_at=? WHERE token_hash=?',(now(),token_hash(raw))); audit(user['id'],'logout','user',user['id']); response=JSONResponse({'ok':True}); response.delete_cookie('cfs_session',path='/'); response.delete_cookie('cfs_csrf',path='/'); return response
@app.get('/api/v1/me')
def me(authorization:str|None=Header(default=None)):
    user,_=session_user(authorization); return {'user':user,'creator':creator_profile(user['id']),'plan':effective_plan(user['id'])}

register_routes(app,db=db,settings=settings,payment_methods=payment_methods,price_service=price_service,payment_verifier=payment_verifier,session_user=session_user,creator_profile=creator_profile,effective_plan=effective_plan,audit=audit,fail=fail,slugify=slugify,now=now,payment_fingerprint=payment_fingerprint,canonical_txid=canonical_txid)
register_platform_routes(app,db=db,settings=settings,scanner=scanner,storage=storage,session_user=session_user,creator_profile=creator_profile,effective_plan=effective_plan,audit=audit,fail=fail,now=now,sha256_bytes=sha256_bytes,verify_password=verify_password)
register_game_edit_routes(app,db=db,session_user=session_user,audit=audit,fail=fail,now=now)
register_payment_extra_routes(app,db=db,settings=settings,payment_methods=payment_methods,session_user=session_user,fail=fail)
register_tropipay_routes(app,db=db,settings=settings,session_user=session_user,creator_profile=creator_profile,audit=audit,fail=fail,now=now)
register_bitshelf_routes(app,db=db,settings=settings,session_user=session_user,fail=fail)
register_prompt_factory_routes(app,db=db,session_user=session_user,audit=audit,fail=fail,now=now)
