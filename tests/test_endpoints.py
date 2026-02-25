"""
Tests for Weather-API endpoints.
External dependencies (RedisCache, OpenWeatherClient) are fully mocked so
no live Redis or OpenWeather connection is needed.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Minimal env so pydantic-settings doesn't require a real .env file
# ---------------------------------------------------------------------------
import os
os.environ.setdefault("OPENWEATHER_API_KEY", "test-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CURRENT = {
    "name": "London",
    "sys": {"country": "GB"},
    "dt": 1700000000,
    "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
    "main": {"temp": 15.0, "feels_like": 14.0, "temp_min": 13.0, "temp_max": 17.0, "pressure": 1013, "humidity": 60},
    "wind": {"speed": 3.5},
    "cod": 200,
}

SAMPLE_FORECAST = {
    "city": {"name": "London", "country": "GB"},
    "list": [
        {
            "dt": 1700000000,
            "main": {"temp": 15.0},
            "weather": [{"description": "clear sky"}],
        }
    ],
    "cod": "200",
}

SAMPLE_GEO = [{"lat": 51.5074, "lon": -0.1278, "name": "London", "country": "GB"}]


def _make_cache_miss():
    mock = MagicMock()
    miss = MagicMock()
    miss.hit = False
    miss.value = None
    mock.get_json.return_value = miss
    mock.acquire_lock.return_value = True
    mock.set_json.return_value = None
    mock.release_lock.return_value = None
    return mock


def _make_cache_hit(payload):
    mock = MagicMock()
    hit = MagicMock()
    hit.hit = True
    hit.value = payload
    hit.age_seconds = 30
    hit.stale = False
    mock.get_json.return_value = hit
    return mock


@pytest.fixture()
def client():
    """TestClient with mocked cache and OW client (cache miss by default)."""
    cache_mock = _make_cache_miss()
    ow_mock = MagicMock()
    ow_mock.geocode_city = AsyncMock(return_value=(51.5074, -0.1278, "London", "GB"))
    ow_mock.get_current = AsyncMock(return_value=SAMPLE_CURRENT)
    ow_mock.get_forecast = AsyncMock(return_value=SAMPLE_FORECAST)

    with patch("app.main.cache", cache_mock), patch("app.main.ow", ow_mock):
        from app.main import app
        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "docs" in resp.json()


# ---------------------------------------------------------------------------
# /v1/weather/current (coord-based) — happy path
# ---------------------------------------------------------------------------

def test_current_weather_coord_happy_path(client):
    resp = client.get("/v1/weather/current?lat=51.5&lon=-0.13&units=metric")
    assert resp.status_code == 200
    data = resp.json()
    assert data["location"]["name"] == "London"
    assert data["units"] == "metric"
    assert "current" in data
    assert data["cache"]["hit"] is False


def test_current_weather_coord_cache_hit():
    cache_mock = _make_cache_hit(SAMPLE_CURRENT)
    ow_mock = MagicMock()

    with patch("app.main.cache", cache_mock), patch("app.main.ow", ow_mock):
        from app.main import app
        with TestClient(app) as c:
            resp = c.get("/v1/weather/current?lat=51.5&lon=-0.13")
    assert resp.status_code == 200
    assert resp.json()["cache"]["hit"] is True


# ---------------------------------------------------------------------------
# /v1/weather/forecast (coord-based) — happy path
# ---------------------------------------------------------------------------

def test_forecast_coord_happy_path(client):
    resp = client.get("/v1/weather/forecast?lat=51.5&lon=-0.13")
    assert resp.status_code == 200
    data = resp.json()
    assert data["location"]["name"] == "London"
    assert "forecast" in data
    assert data["cache"]["hit"] is False


# ---------------------------------------------------------------------------
# /weather?city= — happy path
# ---------------------------------------------------------------------------

def test_weather_by_city_happy_path(client):
    resp = client.get("/weather?city=London")
    assert resp.status_code == 200
    data = resp.json()
    assert data["location"]["name"] == "London"
    assert data["location"]["country"] == "GB"
    assert data["units"] == "metric"


def test_weather_by_city_imperial_units(client):
    resp = client.get("/weather?city=London&units=imperial")
    assert resp.status_code == 200
    assert resp.json()["units"] == "imperial"


# ---------------------------------------------------------------------------
# /forecast?city= — happy path
# ---------------------------------------------------------------------------

def test_forecast_by_city_happy_path(client):
    resp = client.get("/forecast?city=London")
    assert resp.status_code == 200
    data = resp.json()
    assert data["location"]["name"] == "London"
    assert "forecast" in data


# ---------------------------------------------------------------------------
# Input validation — 400 / 422 errors
# ---------------------------------------------------------------------------

def test_missing_city_param(client):
    resp = client.get("/weather")
    assert resp.status_code == 422  # FastAPI validation error


def test_empty_city_param(client):
    resp = client.get("/weather?city=")
    assert resp.status_code == 422


def test_invalid_units_param(client):
    resp = client.get("/weather?city=London&units=kelvin")
    assert resp.status_code == 422


def test_coord_out_of_range_lat(client):
    resp = client.get("/v1/weather/current?lat=999&lon=0")
    assert resp.status_code == 422


def test_coord_out_of_range_lon(client):
    resp = client.get("/v1/weather/current?lat=0&lon=999")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# City not found — 400
# ---------------------------------------------------------------------------

def test_city_not_found_returns_400():
    cache_mock = _make_cache_miss()
    ow_mock = MagicMock()
    ow_mock.geocode_city = AsyncMock(side_effect=ValueError("City not found: 'XxXNotACity'"))

    with patch("app.main.cache", cache_mock), patch("app.main.ow", ow_mock):
        from app.main import app
        with TestClient(app) as c:
            resp = c.get("/weather?city=XxXNotACity")
    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Upstream provider failures — 502 / 503
# ---------------------------------------------------------------------------

def test_upstream_error_returns_502():
    import httpx

    cache_mock = _make_cache_miss()
    ow_mock = MagicMock()
    ow_mock.geocode_city = AsyncMock(return_value=(51.5, -0.13, "London", "GB"))

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    ow_mock.get_current = AsyncMock(
        side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=mock_response)
    )

    with patch("app.main.cache", cache_mock), patch("app.main.ow", ow_mock):
        from app.main import app
        with TestClient(app) as c:
            resp = c.get("/weather?city=London")
    assert resp.status_code == 502


def test_lock_contention_returns_503():
    cache_mock = _make_cache_miss()
    cache_mock.acquire_lock.return_value = False  # simulate lock held by another worker

    ow_mock = MagicMock()
    ow_mock.geocode_city = AsyncMock(return_value=(51.5, -0.13, "London", "GB"))

    with patch("app.main.cache", cache_mock), patch("app.main.ow", ow_mock):
        from app.main import app
        with TestClient(app) as c:
            resp = c.get("/weather?city=London")
    assert resp.status_code == 503
