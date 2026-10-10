import sqlite3
from common.config import db_path, serverless
from threading import Lock
import os

_seed_lock=Lock()
def ensure_database():
    if not serverless(): return
    path=db_path()
    with _seed_lock:
        if path.exists(): return
        from backend.seed.seed import seed
        temporary=path.with_suffix(".seeding.db")
        seed(path=temporary)
        os.replace(temporary,path)

from contextlib import contextmanager
@contextmanager
def connection(readonly=True):
    ensure_database()
    path = db_path()
    conn = sqlite3.connect(f'{path.as_uri()}?mode=ro' if readonly else str(path), uri=readonly)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        yield conn
        if not readonly: conn.commit()
    finally: conn.close()
