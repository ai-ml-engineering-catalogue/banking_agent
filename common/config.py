import os
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
def db_path():
    return Path(os.getenv('DB_PATH', str(ROOT / 'data/bank.db'))).resolve()
def secret():
    return os.getenv('JWT_SECRET', 'local-demo-change-this-secret-before-sharing')
