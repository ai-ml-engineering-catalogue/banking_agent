import sqlite3
from common.config import db_path
from contextlib import contextmanager
@contextmanager
def connection(readonly=True):
    path = db_path()
    conn = sqlite3.connect(f'{path.as_uri()}?mode=ro' if readonly else str(path), uri=readonly)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        yield conn
        if not readonly: conn.commit()
    finally: conn.close()
