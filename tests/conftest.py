import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_fd, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DSO_DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"

from app.database import Base, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
