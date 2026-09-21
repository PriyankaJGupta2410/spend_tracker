from decimal import Decimal as D

import pytest

from app import services


# ---------- pure logic ----------

def test_compute_change_percentage():
    assert services.compute_change(D("150.00"), D("100.00")) == (D("50.00"), D("50.00"))
    assert services.compute_change(D("50.00"), D("100.00")) == (D("-50.00"), D("-50.00"))


def test_compute_change_with_no_previous_spend_has_no_percentage():
    assert services.compute_change(D("50"), D("0")) == (D("50"), None)
    assert services.compute_change(D("0"), D("0")) == (D("0"), None)


def test_previous_month_handles_january_rollover():
    assert services.previous_month("2026-01") == "2025-12"
    assert services.previous_month("2026-09") == "2026-08"


def test_month_range_handles_december():
    start, end = services.month_range("2026-12")
    assert (start.isoformat(), end.isoformat()) == ("2026-12-01", "2027-01-01")


def test_find_spikes_uses_strict_threshold_and_skips_new_categories():
    current = {"food": D("120.00"), "travel": D("110.00"), "fun": D("50.00"), "new": D("90.00")}
    previous = {"food": D("100.00"), "travel": D("100.00"), "fun": D("100.00")}
    # food is exactly +20% (not flagged), travel +10%, fun is down, "new" has no baseline
    assert services.find_spikes(current, previous) == []
    spikes = services.find_spikes({"food": D("120.01")}, {"food": D("100.00")})
    assert [s["category"] for s in spikes] == ["food"]
    assert spikes[0]["change_percent"] == 20.01


# ---------- endpoint ----------

def test_summary_totals_and_categories_for_month(client, add):
    add(100, "food", "2026-09-01")
    add(50.25, "food", "2026-09-20")
    add(200, "travel", "2026-09-10")
    add(999, "food", "2026-08-15")  # other month, must not leak into September
    body = client.get("/summary", params={"month": "2026-09"}).json()

    assert body["month"] == "2026-09"
    assert body["total_spend"] == 350.25
    assert body["all_time_total"] == 1349.25
    assert [(c["category"], c["total"]) for c in body["by_category"]] == [
        ("travel", 200.0), ("food", 150.25),
    ]
    assert body["by_category"][0]["share_percent"] == pytest.approx(57.1, abs=0.1)


def test_summary_month_over_month(client, add):
    add(100, "food", "2026-08-10")
    add(150, "food", "2026-09-10")
    mom = client.get("/summary", params={"month": "2026-09"}).json()["month_over_month"]
    assert mom == {
        "previous_month": "2026-08", "previous_total": 100.0,
        "change_amount": 50.0, "change_percent": 50.0,
    }


def test_summary_with_no_previous_month_data(client, add):
    add(80, "food", "2026-09-10")
    mom = client.get("/summary", params={"month": "2026-09"}).json()["month_over_month"]
    assert mom["previous_total"] == 0
    assert mom["change_percent"] is None


def test_summary_on_empty_database(client):
    body = client.get("/summary", params={"month": "2026-09"}).json()
    assert body["total_spend"] == 0
    assert body["by_category"] == []
    assert body["insights"] == []


def test_summary_january_compares_against_previous_december(client, add):
    add(100, "food", "2025-12-20")
    add(300, "food", "2026-01-05")
    mom = client.get("/summary", params={"month": "2026-01"}).json()["month_over_month"]
    assert mom["previous_month"] == "2025-12"
    assert mom["change_percent"] == 200.0


def test_summary_flags_categories_up_more_than_20_percent(client, add):
    add(100, "food", "2026-08-10")
    add(130, "food", "2026-09-10")     # +30% -> flagged
    add(100, "travel", "2026-08-10")
    add(115, "travel", "2026-09-10")   # +15% -> not flagged
    insights = client.get("/summary", params={"month": "2026-09"}).json()["insights"]
    assert [i["category"] for i in insights] == ["food"]
    assert insights[0]["change_percent"] == 30.0


def test_summary_has_no_floating_point_drift(client, add):
    add(0.1, "food", "2026-09-01")
    add(0.2, "food", "2026-09-02")
    assert client.get("/summary", params={"month": "2026-09"}).json()["total_spend"] == 0.3


@pytest.mark.parametrize("month", ["2026-13", "2026-9", "sept", "2026-00", "1800-01"])
def test_summary_rejects_invalid_month(client, month):
    res = client.get("/summary", params={"month": month})
    assert res.status_code == 422
    assert res.json()["error"] == "validation_error"
