"""Vercel's single FastAPI entry point; local three-service mode stays separate."""
from pathlib import Path
from fastapi import HTTPException
from backend.app.main import app
from mcp_server.server import PerRequestMCP

app.mount('/mcp',PerRequestMCP(),name='mcp')

@app.get('/api/{unknown_path:path}',include_in_schema=False)
def unknown_api(unknown_path: str):
    raise HTTPException(404,detail='NOT_FOUND')

app.frontend('/',directory=str(Path(__file__).parent/'frontend/dist'),fallback='index.html',check_dir=False)
