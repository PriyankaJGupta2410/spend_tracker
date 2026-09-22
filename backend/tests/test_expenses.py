import uuid

import pytest


def test_create_expense_returns_201_and_normalises_category(client):
    res = client.post("/expenses", json={
        "amount": "249.50", "category": "  Food ", "note": " lunch ", "date": "2026-09-01",
    })
    assert res.status_code == 201
    body = res.json()
    assert uuid.UUID(body["id"])  # ids are UUIDs, not sequential
    assert body["amount"] == 249.5
    assert body["category"] == "food"
    assert body["note"] == "lunch"
    assert body["date"] == "2026-09-01"


def test_expense_is_persisted_in_database(client, add):
    add(10, note="coffee")
    res = client.get("/expenses")
    assert [e["note"] for e in res.json()] == ["coffee"]


@pytest.mark.parametrize("payload, field", [
    ({"amount": -5, "category": "food", "date": "2026-09-01"}, "amount"),
    ({"amount": 0, "category": "food", "date": "2026-09-01"}, "amount"),
    ({"amount": 10.999, "category": "food", "date": "2026-09-01"}, "amount"),
    ({"amount": "abc", "category": "food", "date": "2026-09-01"}, "amount"),
    ({"category": "food", "date": "2026-09-01"}, "amount"),
    ({"amount": 10, "category": "   ", "date": "2026-09-01"}, "category"),
    ({"amount": 10, "category": "x" * 51, "date": "2026-09-01"}, "category"),
    ({"amount": 10, "category": "food", "date": "not-a-date"}, "date"),
    ({"amount": 10, "category": "food", "date": "2999-01-01"}, "date"),
    ({"amount": 10, "category": "food"}, "date"),
])
def test_invalid_payloads_are_rejected_with_field_errors(client, payload, field):
    res = client.post("/expenses", json=payload)
    assert res.status_code == 422
    body = res.json()
    assert body["error"] == "validation_error"
    assert field in [d["field"] for d in body["details"]]


def test_invalid_payload_does_not_write_to_database(client):
    client.post("/expenses", json={"amount": -1, "category": "food", "date": "2026-09-01"})
    assert client.get("/expenses").json() == []


def test_list_filters_by_category_case_insensitively(client, add):
    add(10, "food")
    add(20, "travel")
    res = client.get("/expenses", params={"category": "FOOD"})
    assert [e["category"] for e in res.json()] == ["food"]


def test_list_filters_by_inclusive_date_range(client, add):
    add(1, date="2026-08-31")
    add(2, date="2026-09-01")
    add(3, date="2026-09-15")
    add(4, date="2026-09-16")
    res = client.get("/expenses", params={"start_date": "2026-09-01", "end_date": "2026-09-15"})
    assert sorted(e["amount"] for e in res.json()) == [2, 3]


def test_list_combines_category_and_dates_and_sorts_newest_first(client, add):
    add(1, "food", "2026-09-01")
    add(2, "food", "2026-09-10")
    add(3, "travel", "2026-09-05")
    res = client.get("/expenses", params={"category": "food", "start_date": "2026-09-01"})
    assert [e["amount"] for e in res.json()] == [2, 1]


def test_list_rejects_reversed_date_range(client):
    res = client.get("/expenses", params={"start_date": "2026-09-10", "end_date": "2026-09-01"})
    assert res.status_code == 422
    assert "start_date" in res.json()["message"]


def test_list_pagination(client, add):
    for i in range(1, 6):
        add(i)
    res = client.get("/expenses", params={"limit": 2, "offset": 2})
    assert len(res.json()) == 2
    assert client.get("/expenses", params={"limit": 0}).status_code == 422