from datetime import date
from decimal import Decimal
import re
from common.db import connection
from common.money import to_paise

CHANNELS = {'DEBIT_CARD','UPI','NETBANKING','NEFT','IMPS','ATM'}
TYPES = {'PURCHASE','PAYMENT','REFUND','FEE','EMI'}
CATEGORIES = {'Groceries','Dining','Fuel','Shopping','Travel','Entertainment','Utilities','Healthcare','Education','Rent','Salary','Transfer','EMI','Fees','Cash'}

def validate(filters, credit=False):
    allowed = {'from_date','to_date','category','merchant_query','min_amount','max_amount','limit', 'txn_type' if credit else 'channel'}
    if not credit: allowed.add('direction')
    if set(filters)-allowed: raise ValueError('Unknown filter; customer identity cannot be supplied.')
    f = {k:v for k,v in filters.items() if v is not None and v != ''}
    for k in ('from_date','to_date'):
        if k in f:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',f[k]): raise ValueError('Dates must use YYYY-MM-DD')
            date.fromisoformat(f[k])
    if f.get('from_date','0000') > f.get('to_date','9999'): raise ValueError('from_date must precede to_date')
    for k in ('min_amount','max_amount'):
        if k in f and (not Decimal(str(f[k])).is_finite() or f[k]<0): raise ValueError('Amounts must be finite and nonnegative')
    if f.get('min_amount',0)>f.get('max_amount',float('inf')): raise ValueError('min_amount must not exceed max_amount')
    for k,values in [('channel',CHANNELS),('direction',{'DEBIT','CREDIT'}),('txn_type',TYPES)]:
        if k in f and f[k] not in values: raise ValueError(f'Invalid {k}: choose {sorted(values)}')
    if 'category' in f and f['category'] not in CATEGORIES: raise ValueError('Invalid category')
    limit = f.get('limit',20)
    if isinstance(limit,bool) or not isinstance(limit,int) or limit<1: raise ValueError('limit must be a positive integer')
    f['limit']=min(limit,50)
    return f

def transaction_rows(db, customer_id, filters, credit=False, offset=0):
    f = validate(filters,credit)
    table, parent, parentkey = ('credit_card_transactions','cards','card_id') if credit else ('account_transactions','accounts','account_id')
    conditions=['p.customer_id=?']; args=[customer_id]
    for k,op,col in [('from_date','>=','date(t.txn_ts)'),('to_date','<=','date(t.txn_ts)'),('channel','=','t.channel'),('direction','=','t.direction'),('category','=','t.category'),('txn_type','=','t.txn_type'),('min_amount','>=','t.amount_paise'),('max_amount','<=','t.amount_paise')]:
        if k in f:
            conditions.append(f'{col}{op}?'); args.append(to_paise(f[k]) if k.endswith('_amount') else f[k])
    if 'merchant_query' in f:
        conditions.append("instr(lower(t.merchant), lower(?))>0"); args.append(f['merchant_query'])
    query=f"SELECT t.* FROM {table} t JOIN {parent} p ON p.id=t.{parentkey} WHERE {' AND '.join(conditions)} ORDER BY t.txn_ts DESC,t.id DESC LIMIT ? OFFSET ?"
    rows=[dict(r) for r in db.execute(query,args+[f['limit']+1,offset])]
    truncated=len(rows)>f['limit']; rows=rows[:f['limit']]
    for r in rows:
        r['amount']=r.pop('amount_paise')/100; r['currency']='INR'
        if 'balance_after_paise' in r: r['balance_after']=r.pop('balance_after_paise')/100
        r.pop('account_id',None); r.pop('card_id',None)
    return rows,truncated

def credit_details(db, customer_id):
    card=db.execute("SELECT * FROM cards WHERE customer_id=? AND card_type='CREDIT'",(customer_id,)).fetchone()
    if card is None: raise ValueError('No credit card found')
    outstanding=db.execute("SELECT COALESCE(SUM(CASE WHEN txn_type IN ('PAYMENT','REFUND') THEN -amount_paise ELSE amount_paise END),0) FROM credit_card_transactions WHERE card_id=?",(card['id'],)).fetchone()[0]
    statement=db.execute("SELECT * FROM credit_card_statements WHERE card_id=? AND status='UNPAID' ORDER BY due_date LIMIT 1",(card['id'],)).fetchone()
    return {'network':card['network'],'last4':card['last4'],'credit_limit':card['credit_limit_paise']/100,'available_limit':max(0,card['credit_limit_paise']-outstanding)/100,'outstanding':outstanding/100,'next_due_date':statement['due_date'] if statement else None,'min_due':statement['min_due_paise']/100 if statement else 0,'statement_total_due':statement['total_due_paise']/100 if statement else 0,'currency':'INR'}

def banking(customer_id, _offset=0, **filters):
    with connection() as db:
        a=db.execute('SELECT * FROM accounts WHERE customer_id=?',(customer_id,)).fetchone()
        if a is None: raise ValueError('Account not found')
        rows,truncated=transaction_rows(db,customer_id,filters,offset=_offset)
        return {'account':{'masked_number':'••••'+a['account_number'][-4:],'balance':a['balance_paise']/100,'currency':'INR'},'transactions':rows,'summary':{'count':len(rows),'total_debits':round(sum(r['amount'] for r in rows if r['direction']=='DEBIT'),2),'total_credits':round(sum(r['amount'] for r in rows if r['direction']=='CREDIT'),2)},'truncated':truncated}

def credit(customer_id, _offset=0, **filters):
    with connection() as db:
        rows,truncated=transaction_rows(db,customer_id,filters,True,offset=_offset)
        return {'card':credit_details(db,customer_id),'transactions':rows,'summary':{'count':len(rows),'total_spend':round(sum(r['amount'] for r in rows if r['txn_type'] in ('PURCHASE','FEE','EMI')),2),'total_payments':round(sum(r['amount'] for r in rows if r['txn_type']=='PAYMENT'),2),'total_refunds':round(sum(r['amount'] for r in rows if r['txn_type']=='REFUND'),2),'total_reward_points':sum(r['reward_points'] for r in rows)},'truncated':truncated}

def offers(customer_id, category=None, merchant_query=None, card_type=None):
    if category and category not in CATEGORIES: raise ValueError('Invalid category')
    if card_type and card_type not in ('DEBIT','CREDIT','ANY'): raise ValueError('card_type must be DEBIT, CREDIT or ANY')
    with connection() as db:
        cards=[dict(r) for r in db.execute('SELECT card_type,network FROM cards WHERE customer_id=?',(customer_id,))]
        results=[]
        for r in db.execute('SELECT * FROM offers WHERE valid_from<=? AND valid_to>=? ORDER BY id',(date.today().isoformat(),date.today().isoformat())):
            r=dict(r)
            if category and r['category']!=category: continue
            if merchant_query and merchant_query.lower() not in (r['merchant'] or '').lower(): continue
            applicable=[c for c in cards if (not card_type or card_type=='ANY' or c['card_type']==card_type) and (r['eligible_card_type']=='ANY' or r['eligible_card_type']==c['card_type']) and (not r['eligible_network'] or r['eligible_network']==c['network'])]
            if not applicable: continue
            results.append({k:r[k] for k in ('id','title','description','category','merchant','benefit_text','promo_code','terms')} | {'applicable_to':applicable,'valid_till':r['valid_to']})
        return {'offers':results}
