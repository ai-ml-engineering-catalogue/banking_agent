from datetime import date,timedelta
import pytest,jwt
from fastapi.testclient import TestClient
from common.db import connection
from common.auth import create_token,verify_token
from common.money import format_inr
from backend.app.main import app
from mcp_server import queries
client=TestClient(app)

def test_seed_integrity():
    with connection() as db:
        for table,count in [('customers',5),('accounts',5),('cards',10),('credit_card_statements',5),('offers',18)]:
            assert db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]==count
        for uid in range(1,6):
            assert db.execute('SELECT COUNT(*) FROM account_transactions WHERE account_id=?',(uid,)).fetchone()[0]>=40
            assert db.execute('SELECT COUNT(*) FROM credit_card_transactions WHERE card_id=?',(uid*2,)).fetchone()[0]>=25
        assert db.execute('SELECT COUNT(*) FROM offers WHERE valid_to<?',(date.today().isoformat(),)).fetchone()[0]==2
        for uid in range(1,6):
            a=db.execute('SELECT balance_paise FROM accounts WHERE id=?',(uid,)).fetchone()[0]
            b=db.execute('SELECT balance_after_paise FROM account_transactions WHERE account_id=? ORDER BY txn_ts DESC,id DESC LIMIT 1',(uid,)).fetchone()[0]
            assert a==b
    assert format_inr(12345600)=='₹1,23,456.00'

def test_auth_and_isolation():
    for username,password in [('aarav.sharma','Aarav@123'),('priya.iyer','Priya@123'),('rohan.mehta','Rohan@123'),('ananya.reddy','Ananya@123'),('vikram.rathore','Vikram@123')]:
        assert client.post('/api/auth/login',json={'username':username,'password':password}).status_code==200
    assert client.post('/api/auth/login',json={'username':'aarav.sharma','password':'wrong'}).status_code==401
    for endpoint in ['/api/me','/api/accounts','/api/cards','/api/transactions','/api/offers','/api/summary']:
        assert client.get(endpoint).status_code==401
    a=client.get('/api/transactions?limit=50',headers={'Authorization':'Bearer '+create_token(1)}).json()
    b=client.get('/api/transactions?limit=50',headers={'Authorization':'Bearer '+create_token(2)}).json()
    assert not {t['id'] for t in a['transactions']} & {t['id'] for t in b['transactions']}
    assert client.get('/api/me',headers={'Authorization':'Bearer broken'}).status_code==401
    assert verify_token(create_token(3))==3
    assert client.get('/api/transactions?page=2&limit=20',headers={'Authorization':'Bearer '+create_token(1)}).json()['transactions'][0]['id']==a['transactions'][20]['id']

@pytest.mark.parametrize('filters',[{'channel':c} for c in queries.CHANNELS]+[{'direction':'CREDIT'},{'category':'Dining'},{'merchant_query':'Swiggy'},{'min_amount':1000,'max_amount':2500},{'from_date':(date.today()-timedelta(days=20)).isoformat(),'to_date':date.today().isoformat()}])
def test_account_filters(filters):
    data=queries.banking(1,limit=50,**filters)
    for t in data['transactions']:
        for key in ('channel','direction','category'):
            if key in filters: assert t[key]==filters[key]
        if 'merchant_query' in filters: assert filters['merchant_query'].lower() in t['merchant'].lower()
        if 'min_amount' in filters: assert filters['min_amount']<=t['amount']<=filters['max_amount']
        if 'from_date' in filters: assert filters['from_date']<=t['txn_ts'][:10]<=filters['to_date']
    assert data['summary']['total_debits']==round(sum(t['amount'] for t in data['transactions'] if t['direction']=='DEBIT'),2)

@pytest.mark.parametrize('filters',[{'txn_type':t} for t in queries.TYPES]+[{'category':'Dining'},{'merchant_query':'Swiggy'},{'min_amount':600,'max_amount':700},{'from_date':date.today().isoformat()}])
def test_credit_filters(filters):
    data=queries.credit(1,limit=50,**filters)
    for t in data['transactions']:
        for key in ('txn_type','category'):
            if key in filters: assert t[key]==filters[key]
        if 'merchant_query' in filters: assert filters['merchant_query'].lower() in t['merchant'].lower()
        if 'min_amount' in filters: assert filters['min_amount']<=t['amount']<=filters['max_amount']
        if 'from_date' in filters: assert t['txn_ts'][:10]>=filters['from_date']
    assert data['card']['credit_limit']==200000
    assert data['card']['available_limit']+data['card']['outstanding']==200000
    assert data['card']['next_due_date']>date.today().isoformat()
    assert data['summary']['total_spend']==round(sum(t['amount'] for t in data['transactions'] if t['txn_type'] in ('PURCHASE','FEE','EMI')),2)

@pytest.mark.parametrize('filters',[{'from_date':'bad'},{'min_amount':-1},{'min_amount':100,'max_amount':1},{'channel':'WIRE'},{'limit':0},{'direction':'BAD'},{'customer_id':2}])
def test_invalid(filters):
    with pytest.raises((ValueError,TypeError)): queries.banking(1,**filters)

def test_offers_and_readonly():
    offers=queries.offers(1)['offers']
    assert offers
    assert all(o['valid_till']>=date.today().isoformat() for o in offers)
    assert all(c['network']!='RUPAY' for o in offers for c in o['applicable_to'])
    assert all(o['category']=='Dining' for o in queries.offers(1,category='Dining')['offers'])
    assert all('swiggy' in o['merchant'].lower() for o in queries.offers(1,merchant_query='swiggy')['offers'])
    assert all(c['card_type']=='DEBIT' for o in queries.offers(1,card_type='DEBIT')['offers'] for c in o['applicable_to'])
    assert queries.banking(1,limit=100)['summary']['count']==48
    assert queries.banking(1,limit=1)['truncated']
    with connection() as db:
        with pytest.raises(Exception,match='readonly'): db.execute('DELETE FROM customers')

def test_chat_error(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    assert client.post('/api/chat',json={'message':'Hello','session_id':'test'}).status_code==401
    r=client.post('/api/chat',headers={'Authorization':'Bearer '+create_token(1)},json={'message':'Hello','session_id':'test'})
    assert r.status_code==502
    assert r.json()['detail']['error']=='ASSISTANT_UNAVAILABLE'
