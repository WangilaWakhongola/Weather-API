# Weather API

A FastAPI-based Weather API that fetches live data from [OpenWeatherMap](https://openweathermap.org/), caches responses in Redis for faster performance and lower API usage, and exposes endpoints for current weather and 5-day forecasts — addressable by **city name** or **latitude/longitude**.

---

## Features

- **City-name lookup** — `/weather?city=Nairobi` and `/forecast?city=Nairobi`
- **Coordinate-based lookup** — `/v1/weather/current?lat=&lon=` and `/v1/weather/forecast?lat=&lon=`
- **Input validation** — missing/invalid parameters return a clear `400`/`422` response
- **Consistent JSON errors** — upstream failures return `502`; lock contention returns `503`
- **Smart caching** — Redis-backed with configurable TTL and cache-stampede protection
- **Docker support** — full `docker-compose` setup with Redis included
- **Auto documentation** — Swagger UI at `/docs`, ReDoc at `/redoc`
- **Health endpoint** — `/health` for uptime monitoring

---

## Quick Start

### Prerequisites

- Docker & Docker Compose **or** Python 3.11+
- [OpenWeatherMap API key](https://openweathermap.org/appid) (free tier works)

### 1 — Clone & configure

```bash
git clone https://github.com/WangilaWakhongola/Weather-API.git
cd Weather-API
cp env.example .env
# Edit .env and set OPENWEATHER_API_KEY=your_key_here
```

### 2 — Run with Docker Compose

```bash
docker-compose up --build
```

The API is then available at **http://localhost:8000**.

### 3 — Run locally (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Requires a running Redis instance:
redis-server &
uvicorn app.main:app --reload --port 8000
```

---

## API Endpoints

### Health check

```
GET /health
```

```json
{"status": "ok", "service": "weather-api"}
```

---

### Current weather by city name

```
GET /weather?city={city}&units={metric|imperial}
```

| Parameter | Type   | Required | Default  | Description                         |
|-----------|--------|----------|----------|-------------------------------------|
| `city`    | string | ✅       | —        | City name, e.g. `London`            |
| `units`   | string | ❌       | `metric` | `metric` or `imperial`              |

**Example:**

```bash
curl "http://localhost:8000/weather?city=Nairobi&units=metric"
```

```json
{
  "location": {"lat": -1.2864, "lon": 36.8172, "name": "Nairobi", "country": "KE"},
  "units": "metric",
  "current": {
    "weather": [{"main": "Clouds", "description": "few clouds"}],
    "main": {"temp": 24.5, "feels_like": 24.8, "humidity": 65},
    "name": "Nairobi",
    "cod": 200
  },
  "provider": {"name": "openweather"},
  "cache": {"hit": false, "age_seconds": null, "stale": false}
}
```

---

### 5-day forecast by city name

```
GET /forecast?city={city}&units={metric|imperial}
```

```bash
curl "http://localhost:8000/forecast?city=Nairobi"
```

---

### Current weather by coordinates

```
GET /v1/weather/current?lat={lat}&lon={lon}&units={metric|imperial}
```

| Parameter | Type  | Required | Range        |
|-----------|-------|----------|--------------|
| `lat`     | float | ✅       | −90 … 90     |
| `lon`     | float | ✅       | −180 … 180   |
| `units`   | str   | ❌       | metric/imperial |

```bash
curl "http://localhost:8000/v1/weather/current?lat=-1.286389&lon=36.817223"
```

---

### 5-day forecast by coordinates

```
GET /v1/weather/forecast?lat={lat}&lon={lon}&units={metric|imperial}
```

```bash
curl "http://localhost:8000/v1/weather/forecast?lat=-1.286389&lon=36.817223"
```

---

## Error Responses

| Scenario                    | HTTP Status | Example `detail`                    |
|-----------------------------|-------------|--------------------------------------|
| Missing required parameter  | `422`       | FastAPI validation detail            |
| Invalid `units` value       | `422`       | FastAPI validation detail            |
| City not found              | `400`       | `"City not found: 'XxUnknown'"`      |
| OpenWeather API error       | `502`       | Upstream error text                  |
| Cache lock contention       | `503`       | `"Weather refresh in progress, …"`   |

---

## Configuration

Copy `env.example` to `.env` and fill in values:

| Variable                      | Description                             | Default                                      |
|-------------------------------|-----------------------------------------|----------------------------------------------|
| `OPENWEATHER_API_KEY`         | OpenWeatherMap API key (**required**)   | —                                            |
| `OPENWEATHER_BASE_URL`        | OWM data API base URL                   | `https://api.openweathermap.org/data/2.5`    |
| `OPENWEATHER_GEO_URL`         | OWM Geocoding API base URL              | `https://api.openweathermap.org/geo/1.0`     |
| `REDIS_URL`                   | Redis connection URL                    | `redis://localhost:6379/0`                   |
| `CACHE_TTL_CURRENT_SECONDS`   | TTL for current-weather cache           | `120`                                        |
| `CACHE_TTL_FORECAST_SECONDS`  | TTL for forecast cache                  | `900`                                        |
| `CACHE_COORD_ROUND_DECIMALS`  | Decimal places for coordinate rounding  | `2` (~1.1 km precision)                      |

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

All tests use mocks — no live Redis or API key required.

---

## Architecture

```
Client
  │
  ▼
FastAPI app  ──► Redis cache (hit?) ──► return cached
  │                                       │
  │                  (miss)               │
  ▼                                       │
OpenWeather                               │
Geocoding API  (city → lat/lon)           │
  │                                       │
  ▼                                       │
OpenWeather                               │
Data API  ─────────────────────────────► store & return
```

---

## License

MIT
