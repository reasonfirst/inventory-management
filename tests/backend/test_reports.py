"""
Tests for the reports API endpoints and their support for the global filters.
"""
import pytest


class TestQuarterlyReports:
    """Test suite for GET /api/reports/quarterly."""

    def test_unfiltered_covers_all_orders(self, client):
        data = client.get("/api/reports/quarterly").json()

        assert [q["quarter"] for q in data] == ["Q1-2025", "Q2-2025", "Q3-2025", "Q4-2025"]
        assert sum(q["total_orders"] for q in data) == 250

    def test_warehouse_filter(self, client):
        data = client.get("/api/reports/quarterly?warehouse=Tokyo").json()

        assert sum(q["total_orders"] for q in data) == 88

    def test_category_filter(self, client):
        data = client.get("/api/reports/quarterly?category=Sensors").json()

        assert sum(q["total_orders"] for q in data) == 112

    def test_status_filter_sets_full_fulfillment(self, client):
        data = client.get("/api/reports/quarterly?status=Delivered").json()

        assert sum(q["total_orders"] for q in data) == 150
        assert all(q["fulfillment_rate"] == 100.0 for q in data)

    def test_month_filter_keeps_only_its_quarter(self, client):
        data = client.get("/api/reports/quarterly?month=2025-02").json()

        assert len(data) == 1
        assert data[0]["quarter"] == "Q1-2025"
        assert data[0]["total_orders"] == 20

    def test_filter_value_all_is_ignored(self, client):
        data = client.get("/api/reports/quarterly?warehouse=all&category=all&status=all&month=all").json()

        assert sum(q["total_orders"] for q in data) == 250


class TestMonthlyTrends:
    """Test suite for GET /api/reports/monthly-trends."""

    def test_unfiltered_returns_twelve_sorted_months(self, client):
        data = client.get("/api/reports/monthly-trends").json()

        months = [m["month"] for m in data]
        assert months == sorted(months)
        assert len(months) == 12
        assert sum(m["order_count"] for m in data) == 250

    def test_single_month_filter(self, client):
        data = client.get("/api/reports/monthly-trends?month=2025-01").json()

        assert [m["month"] for m in data] == ["2025-01"]
        assert data[0]["order_count"] == 18

    def test_quarter_filter(self, client):
        data = client.get("/api/reports/monthly-trends?month=Q1-2025").json()

        assert [m["month"] for m in data] == ["2025-01", "2025-02", "2025-03"]
        assert sum(m["order_count"] for m in data) == 62

    def test_warehouse_and_category_filters_combine(self, client):
        data = client.get("/api/reports/monthly-trends?warehouse=London&category=Sensors").json()
        orders = client.get("/api/orders?warehouse=London&category=Sensors").json()

        assert sum(m["order_count"] for m in data) == len(orders)
        assert sum(m["revenue"] for m in data) == pytest.approx(sum(o["total_value"] for o in orders))
