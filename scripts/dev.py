"""Run all local services; Ctrl+C terminates every child."""
import subprocess, sys, time, signal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
commands=[[sys.executable,'-m','mcp_server.server'],[sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000'],['npm','run','dev','--prefix','frontend']]
processes=[]
def stop(*_):
    for p in processes:
        if p.poll() is None: p.terminate()
    for p in processes:
        try: p.wait(timeout=5)
        except subprocess.TimeoutExpired: p.kill()
    sys.exit(0)
signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
try:
    for cmd in commands: processes.append(subprocess.Popen(cmd,cwd=ROOT))
    print('\nOpen http://127.0.0.1:5173 · Ctrl+C stops all services',flush=True)
    while all(p.poll() is None for p in processes): time.sleep(.5)
finally: stop()
