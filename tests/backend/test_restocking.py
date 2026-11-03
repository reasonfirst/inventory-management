"""
Tests for the budget-based restocking endpoints.
"""
from datetime import datetime, timedelta

import pytest

import main

# Expected ranking: backlog shortage first, then increasing trend, then larger gap cost.
EXPECTED_ORDER = [
    "WDG-001", "FLT-405", "VLV-506",  # open backlog shortages
    "GSK-203",                         # increasing trend
    "CTL-330", "SNR-420", "PSU-501", "BRG-102",  # stable, by gap cost
]
FULL_COST = 8963.98


@pytest.fixture(autouse=True)
def clear_restock_orders():
    """Submitted orders live in memory; isolate each test."""
    main.restock_orders.clear()
    yield
    main.restock_orders.clear()


class TestRestockRecommendations:
    """Test suite for GET /api/restocking/recommendations."""

    def test_full_budget_recommends_all_candidates_in_rank_order(self, client):
        data = client.get("/api/restocking/recommendations").json()

        assert [i["item_sku"] for i in data["items"]] == EXPECTED_ORDER
        assert data["max_budget"] == pytest.approx(FULL_COST)
        assert data["total_cost"] == pytest.approx(FULL_COST)

    def test_quantity_is_demand_gap(self, client):
        data = client.get("/api/restocking/recommendations").json()
        wdg = next(i for i in data["items"] if i["item_sku"] == "WDG-001")

        assert wdg["quantity"] == 150  # 450 forecasted - 300 current
        assert wdg["line_total"] == pytest.approx(150 * 42.5)
        assert wdg["has_backlog"] is True
        assert wdg["lead_time_days"] == 10

    def test_items_without_demand_growth_are_excluded(self, client):
        data = client.get("/api/restocking/recommendations").json()

        assert "MTR-304" not in [i["item_sku"] for i in data["items"]]

    def test_partial_quantity_for_first_item_that_does_not_fit(self, client):
        data = client.get("/api/restocking/recommendations?budget=7000").json()

        assert [i["item_sku"] for i in data["items"]] == ["WDG-001", "FLT-405"]
        assert data["items"][1]["quantity"] == 50  # floor(625 / 12.40)
        assert data["total_cost"] == pytest.approx(6995.0)

    @pytest.mark.parametrize("budget", [0, 100, 2500, 5000, 7000, 8963.98, 20000])
    def test_total_never_exceeds_budget(self, client, budget):
        data = client.get(f"/api/restocking/recommendations?budget={budget}").json()

        assert data["total_cost"] <= budget + 1e-9
        assert data["max_budget"] == pytest.approx(FULL_COST)

    def test_zero_budget_returns_empty_plan(self, client):
        data = client.get("/api/restocking/recommendations?budget=0").json()

        assert data["items"] == []
        assert data["total_cost"] == 0

    def test_negative_budget_is_rejected(self, client):
        response = client.get("/api/restocking/recommendations?budget=-1")

        assert response.status_code == 400


class TestRestockOrders:
    """Test suite for POST/GET /api/restocking/orders."""

    def test_create_order_uses_server_side_plan(self, client):
        response = client.post("/api/restocking/orders", json={"budget": 7000})

        assert response.status_code == 201
        order = response.json()
        assert order["order_number"] == f"RST-{datetime.now().year}-0001"
        assert order["status"] == "Submitted"
        assert order["total_cost"] == pytest.approx(6995.0)
        assert [i["item_sku"] for i in order["items"]] == ["WDG-001", "FLT-405"]

    def test_expected_delivery_uses_longest_lead_time(self, client):
        order = client.post("/api/restocking/orders", json={"budget": 7000}).json()

        assert order["lead_time_days"] == 10  # WDG-001 (10) vs FLT-405 (6)
        created = datetime.fromisoformat(order["created_date"])
        expected = datetime.fromisoformat(order["expected_delivery"])
        assert expected - created == timedelta(days=10)

    def test_empty_plan_cannot_be_ordered(self, client):
        response = client.post("/api/restocking/orders", json={"budget": 0})

        assert response.status_code == 400
        assert client.get("/api/restocking/orders").json() == []

    def test_list_returns_newest_first(self, client):
        client.post("/api/restocking/orders", json={"budget": 1000})
        client.post("/api/restocking/orders", json={"budget": 7000})

        orders = client.get("/api/restocking/orders").json()
        year = datetime.now().year
        assert [o["order_number"] for o in orders] == [f"RST-{year}-0002", f"RST-{year}-0001"]
