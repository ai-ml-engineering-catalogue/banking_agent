import json
import httpx
import pytest
from langchain_core.messages import AIMessage,HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from agent.context import encode_context,decode_context
from agent.transport import bank_connection
from common.auth import create_token
from common.db import connection
from mcp_server.server import PerRequestMCP

@pytest.fixture
def vercel_mode(monkeypatch,database):
    monkeypatch.setenv('VERCEL','1')
    monkeypatch.setenv('JWT_SECRET','test-only-vercel-secret-with-at-least-32-characters')
    return database

def test_context_encrypted_isolated_and_tamper_proof(vercel_mode):
    token=encode_context([HumanMessage(content='Show UPI payments'),AIMessage(content='Found ₹642.')],1,'chat-a')
    assert 'UPI' not in token
    assert decode_context(token,1,'chat-a')[0].content=='Show UPI payments'
    for cid,sid in [(2,'chat-a'),(1,'chat-b')]:
        with pytest.raises(ValueError): decode_context(token,cid,sid)
    with pytest.raises(ValueError): decode_context(token[:-4]+'abcd',1,'chat-a')

def test_serverless_database_initialization(monkeypatch,tmp_path):
    monkeypatch.setenv('VERCEL','1')
    monkeypatch.setenv('DB_PATH',str(tmp_path/'cold'/'bank.db'))
    with connection() as db:
        assert db.execute('SELECT COUNT(*) FROM customers').fetchone()[0]==5
    # Existing database is reused, not reseeded.
    with connection() as db:
        original=db.execute('SELECT password_hash FROM customers WHERE id=1').fetchone()[0]
    with connection() as db:
        assert db.execute('SELECT password_hash FROM customers WHERE id=1').fetchone()[0]==original

def test_requires_hosted_secret_and_temporary_path(monkeypatch):
    from common.config import secret,db_path
    monkeypatch.setenv('VERCEL','1');monkeypatch.delenv('JWT_SECRET',raising=False)
    with pytest.raises(RuntimeError,match='JWT_SECRET'): secret()
    monkeypatch.setenv('DB_PATH','data/bank.db')
    with pytest.raises(RuntimeError,match='/tmp'): db_path()

async def test_embedded_mcp_auth_filters_and_isolation(vercel_mode):
    ids=[]
    for cid in (1,2):
        async with bank_connection(create_token(cid)) as config:
            assert config['url']=='http://localhost:8001/mcp'
            tools=await MultiServerMCPClient({'bank':config}).get_tools()
            assert {t.name for t in tools}=={'get_banking_transactions','get_credit_card_transactions','get_available_offers'}
            tool=next(t for t in tools if t.name=='get_banking_transactions')
            result=await tool.ainvoke({'channel':'UPI','limit':5})
            if isinstance(result,list): result=result[0]['text']
            data=json.loads(result)
            assert all(t['channel']=='UPI' for t in data['transactions'])
            ids.append({t['id'] for t in data['transactions']})
    assert not ids[0]&ids[1]

async def test_public_mcp_rejects_unauthenticated(vercel_mode):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=PerRequestMCP()),base_url='http://localhost') as client:
        assert (await client.post('/')).status_code==401

async def test_stateless_chat_continuity_without_checkpoint(vercel_mode,monkeypatch):
    import agent.service as service
    from test_agent import FakeModel
    model=FakeModel()
    monkeypatch.setenv('OPENAI_API_KEY','fake-test-key')
    monkeypatch.setattr(service,'ChatOpenAI',lambda **kwargs:model)
    first=await service.run_chat(create_token(1),'vercel-session','Show UPI transactions')
    assert first['tools_used'][0]['name']=='get_banking_transactions'
    # Destroy process-local memory, as with a cold start.
    from langgraph.checkpoint.memory import MemorySaver
    monkeypatch.setattr(service,'memory',MemorySaver())
    second=await service.run_chat(create_token(1),'vercel-session','And last month?',first['context_token'])
    assert len(second['tools_used'])==1
    assert len([m for m in model.histories[-1] if m.type=='human'])==2
    with pytest.raises(ValueError):
        await service.run_chat(create_token(2),'vercel-session','Show data',first['context_token'])

def test_vercel_entrypoint_and_spa():
    from fastapi.testclient import TestClient
    from main import app
    client=TestClient(app)
    assert client.get('/api/me').status_code==401
    assert client.get('/api/unknown').status_code==404
    assert client.get('/chatbot',headers={'Accept':'text/html'}).status_code==200
    assert client.get('/').status_code==200
    assert client.get('/mcp/').status_code==401

async def test_hosted_mcp_protocol_and_api(vercel_mode):
    from main import app
    def factory(headers=None,timeout=None,auth=None):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),headers=headers,timeout=timeout,auth=auth)
    async with factory() as client:
        login=await client.post('http://localhost/api/auth/login',json={'username':'aarav.sharma','password':'Aarav@123'})
        assert login.status_code==200
        token=login.json()['access_token']
        me=await client.get('http://localhost/api/me',headers={'Authorization':'Bearer '+token})
        assert me.json()['username']=='aarav.sharma'
    client=MultiServerMCPClient({'bank':{'url':'http://localhost/mcp/','transport':'streamable_http','headers':{'Authorization':'Bearer '+token},'httpx_client_factory':factory}})
    tools=await client.get_tools()
    assert len(tools)==3
    result=await next(t for t in tools if t.name=='get_credit_card_transactions').ainvoke({'merchant_query':'Swiggy'})
    if isinstance(result,list): result=result[0]['text']
    assert json.loads(result)['card']['last4']=='7390'
