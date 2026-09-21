import os
from pathlib import Path

# Must be set BEFORE the app is imported: settings and the engine are created at import time.
# Tests use a throwaway SQLite file by default. To test against MySQL, set TEST_DATABASE_URL
# (its tables are dropped around every test, so never point it at real data).
TEST_SQLITE = Path(__file__).parent / "test_spend.db"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{TEST_SQLITE}"
os.environ["JWT_SECRET_KEY"] = "pytest-only-secret-key-that-is-long-enough-0123456789"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["BCRYPT_ROUNDS"] = "4"  # fast hashing for tests

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402,F401
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "password123"


def signup(client, username="alice", password=PASSWORD) -> dict:
    """Register + log in, return an Authorization header."""
    client.post("/auth/register", json={"username": username, "password": password})
    res = client.post("/auth/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture(scope="session", autouse=True)
def _cleanup_sqlite_file():
    yield
    engine.dispose()
    TEST_SQLITE.unlink(missing_ok=True)


@pytest.fixture()
def anon():
    """Unauthenticated client on an empty database."""
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:  # startup creates the tables
        yield c
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(anon):
    """Client already logged in as 'alice'."""
    anon.headers.update(signup(anon, "alice"))
    return anon


@pytest.fixture()
def add(client):
    def _add(amount, category="food", date="2026-09-01", note=None):
        body = {"amount": amount, "category": category, "date": date}
        if note is not None:
            body["note"] = note
        res = client.post("/expenses", json=body)
        assert res.status_code == 201, res.text
        return res.json()

    return _add
