import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import CacheInfo, CurrentWeatherResponse, ForecastResponse, Location
from app.services.cache import RedisCache, rounded_coords
from app.services.openweather import OpenWeatherClient

app = FastAPI(title=settings.app_name)

cache = RedisCache(settings.redis_url)
ow = OpenWeatherClient(
    settings.openweather_base_url,
    settings.openweather_api_key,
    settings.openweather_geo_url,
)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/")
def root():
    return JSONResponse({"service": settings.app_name, "docs": "/docs"})


# ── Coord-based endpoints ────────────────────────────────────────────────────

@app.get("/v1/weather/current", response_model=CurrentWeatherResponse)
async def current_weather(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    units: str = Query("metric", pattern="^(metric|imperial)$"),
):
    return await _fetch_current(lat, lon, units)


@app.get("/v1/weather/forecast", response_model=ForecastResponse)
async def forecast(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    units: str = Query("metric", pattern="^(metric|imperial)$"),
):
    return await _fetch_forecast(lat, lon, units)


# ── City-name endpoints ──────────────────────────────────────────────────────

@app.get("/weather", response_model=CurrentWeatherResponse)
async def weather_by_city(
    city: str = Query(..., min_length=1, description="City name, e.g. 'London'"),
    units: str = Query("metric", pattern="^(metric|imperial)$"),
):
    lat, lon, name, country = await _geocode(city)
    return await _fetch_current(lat, lon, units, name=name, country=country)


@app.get("/forecast", response_model=ForecastResponse)
async def forecast_by_city(
    city: str = Query(..., min_length=1, description="City name, e.g. 'London'"),
    units: str = Query("metric", pattern="^(metric|imperial)$"),
):
    lat, lon, name, country = await _geocode(city)
    return await _fetch_forecast(lat, lon, units, name=name, country=country)


# ── Shared helpers ───────────────────────────────────────────────────────────

async def _geocode(city: str):
    """Resolve city name to coordinates; raises 400 on not-found, 502 on upstream error."""
    try:
        return await ow.geocode_city(city)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Geocoding error: {exc.response.text}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Geocoding error: {exc}")


async def _fetch_current(lat: float, lon: float, units: str, *, name: str | None = None, country: str | None = None):
    rlat, rlon = rounded_coords(lat, lon, settings.cache_coord_round_decimals)
    key = f"current:{units}:{rlat}:{rlon}"
    lock_key = f"lock:{key}"

    cached = cache.get_json(key)
    if cached.hit and cached.value is not None:
        payload = cached.value
        return CurrentWeatherResponse(
            location=Location(
                lat=lat, lon=lon,
                name=name or payload.get("name"),
                country=country or payload.get("sys", {}).get("country"),
            ),
            units=units,  # type: ignore
            observed_at=None,
            current=payload,
            provider={"name": "openweather", "data_timestamp": payload.get("dt")},
            cache=CacheInfo(hit=True, age_seconds=cached.age_seconds, stale=cached.stale),
        )

    have_lock = cache.acquire_lock(lock_key, ttl_ms=10_000)
    try:
        if not have_lock:
            raise HTTPException(status_code=503, detail="Weather refresh in progress, try again")

        data = await ow.get_current(lat=lat, lon=lon, units=units)
        cache.set_json(key, data, ttl_seconds=settings.cache_ttl_current_seconds)

        return CurrentWeatherResponse(
            location=Location(
                lat=lat, lon=lon,
                name=name or data.get("name"),
                country=country or data.get("sys", {}).get("country"),
            ),
            units=units,  # type: ignore
            observed_at=None,
            current=data,
            provider={"name": "openweather", "data_timestamp": data.get("dt")},
            cache=CacheInfo(hit=False, age_seconds=None, stale=False),
        )
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=exc.response.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    finally:
        if have_lock:
            cache.release_lock(lock_key)


async def _fetch_forecast(lat: float, lon: float, units: str, *, name: str | None = None, country: str | None = None):
    rlat, rlon = rounded_coords(lat, lon, settings.cache_coord_round_decimals)
    key = f"forecast:{units}:{rlat}:{rlon}"
    lock_key = f"lock:{key}"

    cached = cache.get_json(key)
    if cached.hit and cached.value is not None:
        payload = cached.value
        city_info = payload.get("city", {}) if isinstance(payload, dict) else {}
        return ForecastResponse(
            location=Location(
                lat=lat, lon=lon,
                name=name or city_info.get("name"),
                country=country or city_info.get("country"),
            ),
            units=units,  # type: ignore
            forecast=payload,
            provider={"name": "openweather", "data_timestamp": None},
            cache=CacheInfo(hit=True, age_seconds=cached.age_seconds, stale=cached.stale),
        )

    have_lock = cache.acquire_lock(lock_key, ttl_ms=10_000)
    try:
        if not have_lock:
            raise HTTPException(status_code=503, detail="Forecast refresh in progress, try again")

        data = await ow.get_forecast(lat=lat, lon=lon, units=units)
        cache.set_json(key, data, ttl_seconds=settings.cache_ttl_forecast_seconds)

        city_info = data.get("city", {}) if isinstance(data, dict) else {}
        return ForecastResponse(
            location=Location(
                lat=lat, lon=lon,
                name=name or city_info.get("name"),
                country=country or city_info.get("country"),
            ),
            units=units,  # type: ignore
            forecast=data,
            provider={"name": "openweather", "data_timestamp": None},
            cache=CacheInfo(hit=False, age_seconds=None, stale=False),
        )
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=exc.response.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    finally:
        if have_lock:
            cache.release_lock(lock_key)
