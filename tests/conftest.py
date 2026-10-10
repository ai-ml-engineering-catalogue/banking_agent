import pytest
from backend.seed.seed import seed
@pytest.fixture(scope='session',autouse=True)
def database(tmp_path_factory):
    import os
    path=tmp_path_factory.mktemp('bank')/'bank.db'
    old=os.environ.get('DB_PATH');os.environ['DB_PATH']=str(path)
    seed()
    yield path
    if old is None: os.environ.pop('DB_PATH',None)
    else: os.environ['DB_PATH']=old
