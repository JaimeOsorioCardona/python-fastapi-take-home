"""Integration tests for the Coffee Records API endpoints."""

from fastapi.testclient import TestClient


def test_list_records_default_pagination(client: TestClient) -> None:
    response = client.get("/records")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 9975
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert len(data["items"]) == 20
    assert data["has_next"] is True
    assert data["has_previous"] is False


def test_list_records_custom_pagination(client: TestClient) -> None:
    response = client.get("/records?page=2&page_size=10")
    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 2
    assert data["page_size"] == 10
    assert len(data["items"]) == 10
    assert data["has_next"] is True
    assert data["has_previous"] is True


def test_list_records_country_filter(client: TestClient) -> None:
    response = client.get("/records?country=Germany")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] > 0
    for item in data["items"]:
        assert item["country"] == "Germany"


def test_list_records_multi_gender_filter(client: TestClient) -> None:
    response = client.get("/records?gender=Female&gender=Other")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] > 0
    for item in data["items"]:
        assert item["gender"] in ("Female", "Other")


def test_list_records_numeric_range_filter(client: TestClient) -> None:
    response = client.get("/records?min_age=25&max_age=30")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] > 0
    for item in data["items"]:
        assert 25 <= item["age"] <= 30


def test_list_records_combined_filters(client: TestClient) -> None:
    response = client.get(
        "/records?country=Spain&sleep_quality=Good&smoking=false&min_coffee_intake=2.0"
    )
    assert response.status_code == 200
    data = response.json()

    for item in data["items"]:
        assert item["country"] == "Spain"
        assert item["sleep_quality"] == "Good"
        assert item["smoking"] is False
        assert item["coffee_intake"] >= 2.0


def test_list_records_invalid_range_returns_422(client: TestClient) -> None:
    # min_age greater than max_age
    response = client.get("/records?min_age=50&max_age=30")
    assert response.status_code == 422
    assert "min_age" in response.text

    # min_coffee_intake greater than max_coffee_intake
    response = client.get("/records?min_coffee_intake=10&max_coffee_intake=2")
    assert response.status_code == 422
    assert "min_coffee_intake" in response.text

    # min_bmi greater than max_bmi
    response = client.get("/records?min_bmi=35.0&max_bmi=20.0")
    assert response.status_code == 422
    assert "min_bmi" in response.text


def test_list_records_invalid_pagination_returns_422(client: TestClient) -> None:
    # page must be >= 1
    response = client.get("/records?page=0")
    assert response.status_code == 422

    # page_size must be <= 100
    response = client.get("/records?page_size=500")
    assert response.status_code == 422


def test_get_record_by_id(client: TestClient) -> None:
    response = client.get("/records/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert "country" in data
    assert "coffee_intake" in data

    # Non existent ID returns 404
    missing = client.get("/records/9999999")
    assert missing.status_code == 404


def test_summary_endpoint(client: TestClient) -> None:
    response = client.get("/records/summary?group_by=sleep_quality")
    assert response.status_code == 200
    data = response.json()

    assert data["group_by"] == "sleep_quality"
    assert data["total_groups"] == 4
    group_values = {item["group_value"] for item in data["results"]}
    assert group_values == {"Good", "Fair", "Excellent", "Poor"}

    for item in data["results"]:
        assert item["record_count"] > 0
        assert item["avg_sleep_hours"] > 0
        assert item["avg_caffeine_mg"] >= 0


def test_summary_invalid_group_by_returns_422(client: TestClient) -> None:
    response = client.get("/records/summary?group_by=invalid_column")
    assert response.status_code == 422


def test_list_records_cursor_pagination(client: TestClient) -> None:
    # 1. Fetch first page
    resp1 = client.get("/records?page_size=5")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert len(data1["items"]) == 5
    assert data1["next_cursor"] is not None

    cursor = data1["next_cursor"]
    ids_page1 = [item["id"] for item in data1["items"]]

    # 2. Fetch second page using cursor
    resp2 = client.get(f"/records?cursor={cursor}&page_size=5")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 5
    ids_page2 = [item["id"] for item in data2["items"]]

    # Verify no overlaps and monotonic ordering
    assert set(ids_page1).isdisjoint(set(ids_page2))
    assert min(ids_page2) > max(ids_page1)


def test_list_records_invalid_cursor_returns_422(client: TestClient) -> None:
    resp = client.get("/records?cursor=invalid_base64_***")
    assert resp.status_code == 422
