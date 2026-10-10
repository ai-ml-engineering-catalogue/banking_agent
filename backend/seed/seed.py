from datetime import date, timedelta
from pathlib import Path
import random, sqlite3, bcrypt
from common.config import db_path
from backend.seed.data import USERS, MERCHANTS

def seed(today=None):
    today = today or date.today()
    path = db_path(); path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA foreign_keys=OFF')
        for table in ['account_transactions','credit_card_transactions','credit_card_statements','cards','accounts','offers','customers']:
            db.execute(f'DROP TABLE IF EXISTS {table}')
        db.executescript(Path(__file__).with_name('schema.sql').read_text())
        for uid, user in enumerate(USERS,1):
            name, username, password, city, dn, dl, cn, cl, limit = user
            db.execute('INSERT INTO customers VALUES(?,?,?,?,?,?,?,?)',(uid,username,bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode(),name,f'{username}@example.test',f'900000000{uid}',city,today.isoformat()))
            balance = 18000000 + uid*1000000
            debit, credit = uid*2-1, uid*2
            db.execute('INSERT INTO accounts VALUES(?,?,?,?,?,?,?,?)',(uid,uid,f'90001000{uid:04}', 'DEMO0001234',city,'SAVINGS',balance,(today-timedelta(days=1000)).isoformat()))
            for cid,ctype,network,last4 in [(debit,'DEBIT',dn,dl),(credit,'CREDIT',cn,cl)]:
                db.execute('INSERT INTO cards VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(cid,uid,uid if ctype=='DEBIT' else None,ctype,network,'Platinum' if ctype=='CREDIT' else 'Classic',last4,'12/29','ACTIVE',limit*100 if ctype=='CREDIT' else None,1,16))
            account_rows = []
            for i in range(48):
                merchant, category = MERCHANTS[i%len(MERCHANTS)]
                channel = ['UPI','DEBIT_CARD','NETBANKING','NEFT','IMPS','ATM'][i%6]
                amount = rng.randint(15000,450000); direction='DEBIT'
                if i%16==0: merchant,category,channel,amount,direction='Salary','Salary','NEFT',8500000,'CREDIT'
                elif i%16==1: merchant,category,amount='Monthly rent','Rent',2200000
                elif channel=='ATM': merchant,category,amount='ATM withdrawal','Cash',500000
                elif i%16==2: merchant,category,amount='Home loan','EMI',1200000
                ts = (today-timedelta(days=89-i*89//47)).isoformat()+'T12:00:00'
                account_rows.append((ts, amount,direction,channel,merchant,category))
            start = balance - sum(a if d=='CREDIT' else -a for _,a,d,_,_,_ in account_rows)
            for i,(ts,amount,direction,channel,merchant,category) in enumerate(account_rows):
                start += amount if direction=='CREDIT' else -amount
                db.execute('INSERT INTO account_transactions(account_id,card_id,txn_ts,amount_paise,direction,channel,merchant,description,category,balance_after_paise,reference_no,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(uid,debit if channel=='DEBIT_CARD' else None,ts,amount,direction,channel,merchant,f'{merchant} · fictional transaction',category,start,f'BANK-{uid}-{i:03}','COMPLETED'))
            outstanding = 0
            for i in range(32):
                merchant, category = MERCHANTS[i%9]; amount=rng.randint(10000,300000); kind='PURCHASE'
                if i==0: kind,merchant,category,amount='PAYMENT','Card payment','Transfer',350000
                if i==8: kind,amount='REFUND',25000
                if i==12: kind,merchant,category,amount='FEE','Annual fee','Fees',50000
                if i==20: kind,merchant,category='EMI','Laptop EMI','EMI'
                if i==30: merchant,category,amount='Swiggy','Dining',64200
                if i==31: merchant,category,amount='Amazon','Shopping',489900
                ts=(today-timedelta(days=89-i*89//31)).isoformat()
                outstanding += -amount if kind in ('PAYMENT','REFUND') else amount
                db.execute('INSERT INTO credit_card_transactions(card_id,txn_ts,posted_on,amount_paise,txn_type,merchant,category,description,reference_no,reward_points,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(credit,ts+'T18:30:00',ts,amount,kind,merchant,category,f'{merchant} · fictional transaction',f'CC-{uid}-{i:03}',amount//10000 if kind=='PURCHASE' else 0,'POSTED'))
            db.execute('INSERT INTO credit_card_statements(card_id,period_start,period_end,total_due_paise,min_due_paise,due_date,status) VALUES(?,?,?,?,?,?,?)',(credit,(today-timedelta(days=30)).isoformat(),today.isoformat(),outstanding,max(10000,outstanding//20),(today+timedelta(days=15)).isoformat(),'UNPAID'))
        for i in range(18):
            merchant,category=MERCHANTS[i%9]
            network = ['VISA','MASTERCARD','RUPAY',None][i%4]
            cardtype=['CREDIT','DEBIT','ANY'][i%3]
            db.execute('INSERT INTO offers VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(i+1,f'{merchant}: {10+i%4*5}% back',f'Fictional iBank Demo {category.lower()} offer. Save on your next purchase.',category,merchant,['CASHBACK','DISCOUNT','REWARD_POINTS','EMI'][i%4],f'Up to ₹{250+i*50} benefit',cardtype,network,100000,(today-timedelta(days=30)).isoformat(),(today+timedelta(days=30) if i<16 else today-timedelta(days=1)).isoformat(),f'DEMO{i+1}','Minimum spend ₹1,000. Demo only; no real redemption.'))
    return path
if __name__=='__main__': print(f'Seeded {seed()} with 5 fictional customers.')
