from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import CacheInfo, CurrentWeatherResponse, ForecastResponse, Location
from app.services.cache import RedisCache, rounded_coords
from app.services.openweather import OpenWeatherClient

app = FastAPI(title=settings.app_name)

cache = RedisCache(settings.redis_url)
ow = OpenWeatherClient(settings.openweather_base_url, settings.openweather_api_key)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/v1/weather/current", response_model=CurrentWeatherResponse)
async def current_weather(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    units: str = Query("metric", pattern="^(metric|imperial)$"),
):
    rlat, rlon = rounded_coords(lat, lon, settings.cache_coord_round_decimals)
    key = f"current:{units}:{rlat}:{rlon}"
    lock_key = f"lock:{key}"

    cached = cache.get_json(key)
    if cached.hit and cached.value is not None:
        payload = cached.value
        return CurrentWeatherResponse(
            location=Location(lat=lat, lon=lon, name=payload.get("name"), country=payload.get("sys", {}).get("country")),
            units=units,  # type: ignore
            observed_at=None,
            current=payload,
            provider={"name": "openweather", "data_timestamp": payload.get("dt")},
            cache=CacheInfo(hit=True, age_seconds=cached.age_seconds, stale=cached.stale),
        )

    have_lock = cache.acquire_lock(lock_key, ttl_ms=10_000)
    try:
        if not have_lock:
            # Another request is refreshing; return 503 or wait-and-retry.
            # Keeping it simple: return 503.
            raise HTTPException(status_code=503, detail="Weather refresh in progress, try again")

        data = await ow.get_current(lat=lat, lon=lon, units=units)
        cache.set_json(key, data, ttl_seconds=settings.cache_ttl_current_seconds)

        return CurrentWeatherResponse(
            location=Location(lat=lat, lon=lon, name=data.get("name"), country=data.get("sys", {}).get("country")),
            units=units,  # type: ignore
            observed_at=None,
            current=data,
            provider={"name": "openweather", "data_timestamp": data.get("dt")},
            cache=CacheInfo(hit=False, age_seconds=None, stale=False),
        )
    except httpx.HTTPStatusError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        if have_lock:
            cache.release_lock(lock_key)


@app.get("/v1/weather/forecast", response_model=ForecastResponse)
async def forecast(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    units: str = Query("metric", pattern="^(metric|imperial)$"),
):
    rlat, rlon = rounded_coords(lat, lon, settings.cache_coord_round_decimals)
    key = f"forecast:{units}:{rlat}:{rlon}"
    lock_key = f"lock:{key}"

    cached = cache.get_json(key)
    if cached.hit and cached.value is not None:
        payload = cached.value
        city = payload.get("city", {}) if isinstance(payload, dict) else {}
        return ForecastResponse(
            location=Location(lat=lat, lon=lon, name=city.get("name"), country=city.get("country")),
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

        city = data.get("city", {}) if isinstance(data, dict) else {}
        return ForecastResponse(
            location=Location(lat=lat, lon=lon, name=city.get("name"), country=city.get("country")),
            units=units,  # type: ignore
            forecast=data,
            provider={"name": "openweather", "data_timestamp": None},
            cache=CacheInfo(hit=False, age_seconds=None, stale=False),
        )
    except httpx.HTTPStatusError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        if have_lock:
            cache.release_lock(lock_key)


# Optional: nicer error for root
@app.get("/")
def root():
    return JSONResponse({"service": settings.app_name, "docs": "/docs"})