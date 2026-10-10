import asyncio,json,socket
import httpx,pytest,uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp_server.server import app
from common.auth import create_token

async def test_mcp_http_transport_and_identity():
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
    task=asyncio.create_task(server.serve(sockets=[sock]))
    try:
        for _ in range(100):
            if server.started: break
            await asyncio.sleep(.02)
        url=f'http://127.0.0.1:{port}/mcp'
        async with httpx.AsyncClient() as client:
            assert (await client.post(url,json={})).status_code==401
            assert (await client.post(url,json={},headers={'Authorization':'Bearer invalid'})).status_code==401
        ids=[]
        for customer in (1,2):
            async with streamablehttp_client(url,headers={'Authorization':'Bearer '+create_token(customer)}) as (read,write,_):
                async with ClientSession(read,write) as session:
                    await session.initialize()
                    tools=(await session.list_tools()).tools
                    assert {t.name for t in tools}=={'get_banking_transactions','get_credit_card_transactions','get_available_offers'}
                    assert all('customer_id' not in t.inputSchema['properties'] for t in tools)
                    result=await session.call_tool('get_banking_transactions',{'limit':50})
                    assert not result.isError
                    data=json.loads(result.content[0].text)
                    ids.append({t['id'] for t in data['transactions']})
                    result=await session.call_tool('get_credit_card_transactions',{'merchant_query':'Swiggy'})
                    assert not result.isError
                    result=await session.call_tool('get_available_offers',{'category':'Dining'})
                    assert not result.isError
        assert not ids[0]&ids[1]
    finally:
        server.should_exit=True
        await task
