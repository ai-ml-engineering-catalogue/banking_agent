from datetime import datetime, timedelta, timezone
import jwt
from common.config import secret

def create_token(customer_id):
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': str(customer_id), 'iat': now, 'exp': now + timedelta(minutes=60)}, secret(), algorithm='HS256')
def verify_token(token):
    payload = jwt.decode(token, secret(), algorithms=['HS256'], options={'require': ['sub', 'exp', 'iat']})
    customer = int(payload['sub'])
    if customer <= 0: raise ValueError('Invalid customer')
    return customer
