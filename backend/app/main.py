import logging
import bcrypt, jwt
from fastapi import FastAPI, Depends, HTTPException, Query, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from common.auth import create_token, verify_token
from common.db import connection
from mcp_server import queries
from agent.service import run_chat
from agent.context import ContextError
from agent import voice
app=FastAPI(title='iBank Demo API')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['GET','POST'],allow_headers=['Authorization','Content-Type'])
bearer=HTTPBearer(auto_error=False)
def auth(credentials: HTTPAuthorizationCredentials | None=Depends(bearer)):
    try:
        if not credentials or credentials.scheme.lower()!='bearer': raise ValueError()
        cid=verify_token(credentials.credentials)
        with connection() as db:
            if not db.execute('SELECT id FROM customers WHERE id=?',(cid,)).fetchone(): raise ValueError()
        return cid,credentials.credentials
    except (jwt.PyJWTError,ValueError): raise HTTPException(401,detail='UNAUTHORIZED')
class Speak(BaseModel):
    text: str=Field(min_length=1,max_length=20000)
class Login(BaseModel):
    username: str=Field(max_length=100)
    password: str=Field(max_length=100)
class Chat(BaseModel):
    context_token: str | None=Field(default=None,max_length=100000)
    message: str=Field(min_length=1,max_length=2000)
    session_id: str=Field(min_length=1,max_length=100,pattern=r'^[a-zA-Z0-9_-]+$')
@app.post('/api/auth/login')
def login(body: Login):
    with connection() as db:
        user=db.execute('SELECT * FROM customers WHERE username=?',(body.username,)).fetchone()
        if not user or len(body.password.encode())>72 or not bcrypt.checkpw(body.password.encode(),user['password_hash'].encode()): raise HTTPException(401,detail='INVALID_CREDENTIALS')
        return {'access_token':create_token(user['id']),'token_type':'bearer','customer':{'full_name':user['full_name']}}
@app.get('/api/me')
def me(user=Depends(auth)):
    with connection() as db: return dict(db.execute('SELECT full_name,username,email,city FROM customers WHERE id=?',(user[0],)).fetchone())
@app.get('/api/accounts')
def accounts(user=Depends(auth)):
    return queries.banking(user[0],limit=1)['account']
@app.get('/api/cards')
def cards(user=Depends(auth)):
    with connection() as db:
        result=[dict(r) for r in db.execute('SELECT card_type,network,variant,last4,expiry,status FROM cards WHERE customer_id=?',(user[0],))]
        for r in result:
            if r['card_type']=='CREDIT': r.update(queries.credit_details(db,user[0]))
        return {'cards':result}
@app.get('/api/transactions')
def transactions(source: str=Query('account',pattern='^(account|credit)$'), from_date: str|None=None,to_date: str|None=None,channel: str|None=None,category: str|None=None,merchant_query: str|None=None,min_amount: float|None=None,max_amount: float|None=None,direction: str|None=None,txn_type: str|None=None,limit: int=20,page: int=Query(1,ge=1),user=Depends(auth)):
    f={'from_date':from_date,'to_date':to_date,'category':category,'merchant_query':merchant_query,'min_amount':min_amount,'max_amount':max_amount,'limit':limit}
    if source=='account': f.update(channel=channel,direction=direction)
    else: f.update(txn_type=txn_type)
    try:
        validated=queries.validate(f, source=='credit')
        result=(queries.banking if source=='account' else queries.credit)(user[0],_offset=(page-1)*validated['limit'],**f)
        return result
    except ValueError as exc: raise HTTPException(422,detail=str(exc))
@app.get('/api/offers')
def offers(category: str|None=None,merchant_query: str|None=None,card_type: str|None=None,user=Depends(auth)):
    try: return queries.offers(user[0],category,merchant_query,card_type)
    except ValueError as exc: raise HTTPException(422,detail=str(exc))
@app.get('/api/summary')
def summary(user=Depends(auth)):
    from datetime import date,timedelta
    start=(date.today()-timedelta(days=29)).isoformat()
    with connection() as db:
        rows=db.execute("SELECT category,SUM(amount_paise)/100.0 AS amount FROM (SELECT t.category,t.amount_paise FROM account_transactions t JOIN accounts a ON t.account_id=a.id WHERE a.customer_id=? AND t.direction='DEBIT' AND date(t.txn_ts)>=? UNION ALL SELECT t.category,t.amount_paise FROM credit_card_transactions t JOIN cards c ON t.card_id=c.id WHERE c.customer_id=? AND t.txn_type IN ('PURCHASE','FEE','EMI') AND date(t.txn_ts)>=?) GROUP BY category ORDER BY amount DESC",(user[0],start,user[0],start))
        return {'categories':[dict(r) for r in rows],'period_start':start}
@app.post('/api/chat')
async def chat(body: Chat,user=Depends(auth)):
    try: return await run_chat(user[1],body.session_id,body.message,body.context_token)
    except ContextError as exc: raise HTTPException(422,detail=str(exc))
    except Exception:
        logging.getLogger(__name__).warning('Assistant request failed; verify MCP connectivity and OpenAI configuration.')
        raise HTTPException(502,detail={'error':'ASSISTANT_UNAVAILABLE','message':'The assistant is unavailable. Check the MCP service and server-side OpenAI key, then try again.'})
def voice_unavailable():
    logging.getLogger(__name__).warning('Voice request failed; verify OpenAI configuration and audio model access.')
    return HTTPException(502,detail={'error':'VOICE_UNAVAILABLE','message':'Voice is unavailable right now. You can still type your question.'})
@app.post('/api/voice/transcribe')
async def transcribe(request: Request,user=Depends(auth)):
    if int(request.headers.get('content-length') or 0)>voice.MAX_AUDIO_BYTES: raise HTTPException(413,detail='Recording is too long. Keep voice questions under a minute.')
    audio=bytearray()
    async for chunk in request.stream():
        audio+=chunk
        if len(audio)>voice.MAX_AUDIO_BYTES: raise HTTPException(413,detail='Recording is too long. Keep voice questions under a minute.')
    try: return {'text':await voice.transcribe(bytes(audio),request.headers.get('content-type',''))}
    except voice.VoiceError as exc: raise HTTPException(422,detail=str(exc))
    except Exception: raise voice_unavailable()
@app.post('/api/voice/speak')
async def speak(body: Speak,user=Depends(auth)):
    try: audio=await voice.speak(body.text)
    except voice.VoiceError as exc: raise HTTPException(422,detail=str(exc))
    except Exception: raise voice_unavailable()
    return Response(audio,media_type='audio/mpeg',headers={'Cache-Control':'no-store'})
