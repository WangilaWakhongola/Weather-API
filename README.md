\# Weather API (FastAPI + Redis + OpenWeather)



Fetches live weather data from OpenWeather, caches results in Redis with TTL, and serves through your own API.



\## Features

\- `GET /v1/weather/current` (by `lat/lon`)

\- `GET /v1/weather/forecast` (5-day / 3-hour forecast from OpenWeather)

\- Redis caching with TTL + simple lock to avoid cache stampede

\- Docker + docker-compose (API + Redis)

\- Health endpoint `GET /health`



\## Prerequisites

\- OpenWeather API key: https://openweathermap.org/api

\- Docker (recommended) OR Python 3.11+



\## Configuration

Copy env example:

```bash

cp .env.example .env

```



Set:

\- `OPENWEATHER\_API\_KEY=...`



\## Run with Docker (recommended)

```bash

docker compose up --build

```



API: http://localhost:8000  

Docs: http://localhost:8000/docs



\## Run locally (without Docker)

```bash

python -m venv .venv

source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

pip install -r requirements.txt



export $(cat .env | xargs)  # Linux/macOS (or set env vars manually)

uvicorn app.main:app --reload --port 8000

```



Make sure Redis is running (default: `redis://localhost:6379/0`).



\## Endpoints



\### Current weather

```bash

curl "http://localhost:8000/v1/weather/current?lat=-1.286389\&lon=36.817223\&units=metric"

```



\### Forecast (OpenWeather 5-day/3-hour)

```bash

curl "http://localhost:8000/v1/weather/forecast?lat=-1.286389\&lon=36.817223\&units=metric"

```



\## Notes

\- OpenWeather "forecast" endpoint is 5-day / 3-hour forecast unless you use their One Call API (different subscription).

\- Coordinate rounding is used to increase cache hit rate (configurable via env).

"# Weather-API" 
