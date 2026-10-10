from contextlib import asynccontextmanager
import httpx
from common.config import serverless
import os

@asynccontextmanager
async def bank_connection(token):
    config={'url':os.getenv('MCP_URL','http://127.0.0.1:8001/mcp'),'transport':'streamable_http','headers':{'Authorization':f'Bearer {token}'}}
    if not serverless():
        yield config
        return
    from mcp_server.server import create_mcp
    server,app=create_mcp()
    def factory(headers=None,timeout=None,auth=None):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),headers=headers,timeout=timeout,auth=auth)
    config.update(url='http://localhost:8001/mcp',httpx_client_factory=factory)
    async with server.session_manager.run():
        yield config
