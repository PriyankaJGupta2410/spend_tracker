import datetime as dt

import jwt
import pytest

from app import config
from tests.conftest import PASSWORD, signup

EXPENSE = {"amount": 5, "category": "food", "date": "2026-09-01"}


# ---------- registration ----------

def test_register_returns_user_without_password(anon):
    res = anon.post("/auth/register", json={"username": "Alice_1", "password": PASSWORD})
    assert res.status_code == 201
    assert res.json() == {"id": 1, "username": "alice_1"}


def test_register_duplicate_username_is_409_case_insensitive(anon):
    anon.post("/auth/register", json={"username": "alice", "password": PASSWORD})
    res = anon.post("/auth/register", json={"username": "ALICE", "password": PASSWORD})
    assert res.status_code == 409
    assert res.json()["error"] == "http_error"


@pytest.mark.parametrize("payload, field", [
    ({"username": "ab", "password": PASSWORD}, "username"),
    ({"username": "bad name!", "password": PASSWORD}, "username"),
    ({"username": "alice", "password": "short"}, "password"),
    ({"username": "alice", "password": "x" * 73}, "password"),
    ({"username": "alice", "password": "é" * 40}, "password"),   # 80 bytes
    ({"password": PASSWORD}, "username"),
])
def test_register_validation(anon, payload, field):
    res = anon.post("/auth/register", json=payload)
    assert res.status_code == 422
    assert field in [d["field"] for d in res.json()["details"]]


def test_password_is_stored_hashed(anon):
    from app.database import SessionLocal
    from app.models import User

    anon.post("/auth/register", json={"username": "alice", "password": PASSWORD})
    with SessionLocal() as db:
        stored = db.query(User).one().password_hash
    assert stored != PASSWORD and stored.startswith("$2")


# ---------- login ----------

def test_login_returns_bearer_token(anon):
    anon.post("/auth/register", json={"username": "alice", "password": PASSWORD})
    res = anon.post("/auth/login", json={"username": "Alice", "password": PASSWORD})
    body = res.json()
    assert res.status_code == 200
    assert body["token_type"] == "bearer" and body["expires_in"] == 3600
    payload = jwt.decode(body["access_token"], config.JWT_SECRET_KEY, algorithms=["HS256"])
    assert payload["sub"] == "1"


def test_wrong_password_and_unknown_user_get_same_401(anon):
    anon.post("/auth/register", json={"username": "alice", "password": PASSWORD})
    wrong = anon.post("/auth/login", json={"username": "alice", "password": "nope-nope"})
    unknown = anon.post("/auth/login", json={"username": "ghost", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


# ---------- protected routes ----------

@pytest.mark.parametrize("method, path", [
    ("get", "/expenses"), ("post", "/expenses"), ("get", "/summary"), ("get", "/auth/me"),
])
def test_protected_routes_reject_missing_token(anon, method, path):
    res = getattr(anon, method)(path)
    assert res.status_code == 401
    assert res.headers["www-authenticate"] == "Bearer"


def test_garbage_token_is_rejected(anon):
    res = anon.get("/expenses", headers={"Authorization": "Bearer not.a.token"})
    assert res.status_code == 401


def test_token_signed_with_wrong_secret_is_rejected(anon):
    anon.post("/auth/register", json={"username": "alice", "password": PASSWORD})
    forged = jwt.encode({"sub": "1", "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)},
                        "some-other-secret-that-is-long-enough-0123456", algorithm="HS256")
    assert anon.get("/expenses", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_expired_token_is_rejected(anon):
    anon.post("/auth/register", json={"username": "alice", "password": PASSWORD})
    expired = jwt.encode({"sub": "1", "exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=5)},
                         config.JWT_SECRET_KEY, algorithm="HS256")
    assert anon.get("/expenses", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_token_without_expiry_is_rejected(anon):
    anon.post("/auth/register", json={"username": "alice", "password": PASSWORD})
    no_exp = jwt.encode({"sub": "1"}, config.JWT_SECRET_KEY, algorithm="HS256")
    assert anon.get("/expenses", headers={"Authorization": f"Bearer {no_exp}"}).status_code == 401


def test_token_for_nonexistent_user_is_rejected(anon):
    token = jwt.encode({"sub": "999", "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)},
                       config.JWT_SECRET_KEY, algorithm="HS256")
    assert anon.get("/expenses", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_me_returns_current_user(client):
    assert client.get("/auth/me").json()["username"] == "alice"


def test_health_and_auth_routes_are_public(anon):
    assert anon.get("/health").status_code == 200


# ---------- data isolation ----------

def test_users_only_see_their_own_expenses_and_summary(client):
    bob = signup(client, "bob")
    client.post("/expenses", json={**EXPENSE, "amount": 100})                 # alice
    client.post("/expenses", json={**EXPENSE, "amount": 7}, headers=bob)     # bob

    alice_items = client.get("/expenses").json()
    bob_items = client.get("/expenses", headers=bob).json()
    assert [e["amount"] for e in alice_items] == [100]
    assert [e["amount"] for e in bob_items] == [7]

    bob_summary = client.get("/summary", params={"month": "2026-09"}, headers=bob).json()
    assert bob_summary["total_spend"] == 7
    assert bob_summary["all_time_total"] == 7
