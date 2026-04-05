from typing import Any, Dict, List, Optional, Tuple

import httpx


class OpenWeatherClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        geo_url: str = "https://api.openweathermap.org/geo/1.0",
        timeout_seconds: float = 5.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.geo_url = geo_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout_seconds

    async def geocode_city(self, city: str) -> Tuple[float, float, str, str]:
        """Resolve a city name to (lat, lon, city_name, country) via the Geocoding API."""
        url = f"{self.geo_url}/direct"
        params = {"q": city, "limit": 1, "appid": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            results: List[Dict[str, Any]] = r.json()

        if not results:
            raise ValueError(f"City not found: {city!r}")

        loc = results[0]
        return loc["lat"], loc["lon"], loc.get("name", city), loc.get("country", "")

    async def get_current(self, lat: float, lon: float, units: str) -> Dict[str, Any]:
        url = f"{self.base_url}/weather"
        params = {"lat": lat, "lon": lon, "units": units, "appid": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()

    async def get_forecast(self, lat: float, lon: float, units: str) -> Dict[str, Any]:
        url = f"{self.base_url}/forecast"
        params = {"lat": lat, "lon": lon, "units": units, "appid": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()
