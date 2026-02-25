Weather API
A robust weather API service that fetches real-time weather data from OpenWeather and caches responses in Redis for optimal performance. Built with FastAPI and Docker.

Features
Real-time Weather Data: Fetch current weather conditions using latitude/longitude coordinates

5-Day Forecast: Get 3-hour interval weather forecasts for the next 5 days

Smart Caching: Redis-based caching with configurable TTL to reduce API calls

Cache Stampede Protection: Implements a simple locking mechanism to prevent cache stampede

Docker Support: Full containerization with docker-compose for easy deployment

Auto Documentation: Interactive API docs with Swagger UI and ReDoc

Health Check: Built-in health endpoint for monitoring

Quick Start
Prerequisites
Docker and Docker Compose

OpenWeather API key (Get one here)

Installation
Clone the repository

bash
git clone https://github.com/yourusername/weather-api.git
cd weather-api
Set up environment variables

bash
cp .env.example .env
Edit .env and add your OpenWeather API key:

env
OPENWEATHER_API_KEY=your_api_key_here
Run with Docker Compose

bash
docker-compose up --build
Access the API

API Base URL: http://localhost:8000

Interactive Docs: http://localhost:8000/docs

Alternative Docs: http://localhost:8000/redoc

Docker Configuration
Dockerfile
dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
docker-compose.yml
yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_DB=0
      - OPENWEATHER_API_KEY=${OPENWEATHER_API_KEY}
      - CACHE_TTL_SECONDS=300
      - COORDINATE_ROUNDING=2
    volumes:
      - ./app:/app/app
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - weather-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - weather-network

networks:
  weather-network:
    driver: bridge
API Endpoints
Health Check
bash
GET /health
Response

json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "services": {
    "redis": "connected",
    "openweather": "available"
  }
}
Current Weather
bash
GET /v1/weather/current?lat={latitude}&lon={longitude}&units={units}
Parameters

Parameter	Type	Required	Description	Default
lat	float	Yes	Latitude (-90 to 90)	-
lon	float	Yes	Longitude (-180 to 180)	-
units	string	No	Units: metric, imperial, or standard	metric
Example Request

bash
curl "http://localhost:8000/v1/weather/current?lat=-1.286389&lon=36.817223&units=metric"
Example Response

json
{
  "coord": { "lon": 36.8172, "lat": -1.2864 },
  "weather": [
    {
      "id": 801,
      "main": "Clouds",
      "description": "few clouds",
      "icon": "02d"
    }
  ],
  "main": {
    "temp": 24.5,
    "feels_like": 24.8,
    "temp_min": 23.9,
    "temp_max": 25.1,
    "pressure": 1015,
    "humidity": 65
  },
  "name": "Nairobi",
  "cod": 200
}
5-Day Forecast
bash
GET /v1/weather/forecast?lat={latitude}&lon={longitude}&units={units}
Parameters

Parameter	Type	Required	Description	Default
lat	float	Yes	Latitude (-90 to 90)	-
lon	float	Yes	Longitude (-180 to 180)	-
units	string	No	Units: metric, imperial, or standard	metric
Example Request

bash
curl "http://localhost:8000/v1/weather/forecast?lat=-1.286389&lon=36.817223&units=metric"
Configuration
Environment Variables
Variable	Description	Default
OPENWEATHER_API_KEY	Your OpenWeather API key	Required
REDIS_HOST	Redis server hostname	localhost
REDIS_PORT	Redis server port	6379
REDIS_DB	Redis database number	0
CACHE_TTL_SECONDS	Cache expiration time	300 (5 minutes)
COORDINATE_ROUNDING	Decimal places for coord rounding	2 (~1.1km precision)
Coordinate Rounding
The API rounds coordinates to increase cache hit rates. With the default setting of 2 decimal places:

Precision: ~1.1 kilometers at the equator

Cache key: weather:current:-1.29,36.82:metric

Benefit: Multiple nearby requests share the same cached response

Architecture
text
┌─────────────┐     ┌──────────┐     ┌─────────────┐
│   Client    │────▶│  FastAPI │────▶│    Redis    │
└─────────────┘     └──────────┘     └─────────────┘
                           │                  │
                           ▼                  │
                    ┌─────────────┐           │
                    │ OpenWeather │◀──────────┘
                    │     API     │   (Cache Miss)
                    └─────────────┘
Caching Strategy
Check Cache: API checks Redis for cached response

Cache Hit: Returns cached data immediately

Cache Miss:

Acquires a distributed lock

Fetches from OpenWeather API

Stores in Redis with TTL

Releases the lock

Cache Stampede Prevention: Concurrent requests for the same data wait for the first request to complete

Local Development (Without Docker)
Create virtual environment

bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install dependencies

bash
pip install -r requirements.txt
Set environment variables

bash
export $(cat .env | xargs)  # On Windows: set OPENWEATHER_API_KEY=your_key
Run Redis (make sure Redis is installed and running)

bash
redis-server
Start the API server

bash
uvicorn app.main:app --reload --port 8000
Dependencies
Create a requirements.txt file:

txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
redis==5.0.1
httpx==0.25.1
pydantic==2.4.2
pydantic-settings==2.1.0
python-dotenv==1.0.0
tenacity==8.2.3
Environment File
Create a .env.example file:

env
OPENWEATHER_API_KEY=your_api_key_here
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
CACHE_TTL_SECONDS=300
COORDINATE_ROUNDING=2
Notes
OpenWeather "forecast" endpoint provides 5-day forecast with 3-hour intervals

Coordinate rounding is used to increase cache hit rate (configurable via env)

Free OpenWeather tier allows 60 calls/minute - caching helps stay within limits

License
MIT
