from contextvars import ContextVar
import jwt, uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse
from common.auth import verify_token
from common.db import connection
from mcp_server import queries
identity = ContextVar('customer_id')
mcp = FastMCP('iBank Demo', stateless_http=True, json_response=True)

@mcp.tool()
def get_banking_transactions(from_date: str | None=None, to_date: str | None=None, channel: str | None=None, category: str | None=None, merchant_query: str | None=None, min_amount: float | None=None, max_amount: float | None=None, direction: str | None=None, limit: int=20) -> dict:
    """Read the authenticated customer's savings/debit activity. Dates YYYY-MM-DD inclusive; amounts in INR. Channels: DEBIT_CARD, UPI, NETBANKING, NEFT, IMPS, ATM. Direction DEBIT/CREDIT. Example: channel='UPI', limit=5. Summary covers returned rows only; truncated means narrow filters before asserting an exhaustive total. Never accepts an identity."""
    return queries.banking(identity.get(), **{k:v for k,v in locals().items()})

@mcp.tool()
def get_credit_card_transactions(from_date: str | None=None, to_date: str | None=None, category: str | None=None, merchant_query: str | None=None, min_amount: float | None=None, max_amount: float | None=None, txn_type: str | None=None, limit: int=20) -> dict:
    """Read own credit card purchases, payments, refunds, fees and EMIs plus limit, outstanding and statement due date. Dates YYYY-MM-DD; amounts INR. txn_type: PURCHASE/PAYMENT/REFUND/FEE/EMI. Example merchant_query='Swiggy'. Summary covers returned rows only, max 50; do not claim complete totals when truncated."""
    return queries.credit(identity.get(), **{k:v for k,v in locals().items()})

@mcp.tool()
def get_available_offers(category: str | None=None, merchant_query: str | None=None, card_type: str | None=None) -> dict:
    """List currently valid fictional offers eligible for own card types and networks. Optional category (e.g. Dining, Travel), merchant substring, card_type DEBIT/CREDIT/ANY. Does not redeem offers."""
    return queries.offers(identity.get(),category,merchant_query,card_type)

class BearerAuth:
    def __init__(self, app): self.app=app
    async def __call__(self, scope, receive, send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        headers=dict(scope['headers']); auth=headers.get(b'authorization',b'').decode()
        try:
            if not auth.startswith('Bearer '): raise ValueError('Missing bearer token')
            cid=verify_token(auth[7:])
            with connection() as db:
                if not db.execute('SELECT id FROM customers WHERE id=?',(cid,)).fetchone(): raise ValueError('Unknown customer')
        except (jwt.PyJWTError,ValueError):
            return await JSONResponse({'error':'UNAUTHORIZED'},status_code=401)(scope,receive,send)
        marker=identity.set(cid)
        try: await self.app(scope,receive,send)
        finally: identity.reset(marker)
app=BearerAuth(mcp.streamable_http_app())
if __name__=='__main__': uvicorn.run(app,host='127.0.0.1',port=8001)
