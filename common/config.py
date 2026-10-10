import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
def db_path():
    default='/tmp/ibank-demo/bank.db' if serverless() else str(ROOT / 'data/bank.db')
    path=Path(os.getenv('DB_PATH',default)).resolve()
    if serverless() and not any(path.is_relative_to(root) for root in (Path('/tmp').resolve(),Path(tempfile.gettempdir()).resolve())):
        raise RuntimeError('On Vercel DB_PATH must be inside /tmp, or left unset.')
    return path
def serverless():
    return os.getenv('VERCEL')=='1'
def secret():
    value=os.getenv('JWT_SECRET', 'local-demo-change-this-secret-before-sharing')
    if serverless() and (len(value)<32 or value=='local-demo-change-this-secret-before-sharing'):
        raise RuntimeError('Set a random JWT_SECRET of at least 32 characters on Vercel.')
    return value
