from typing import Any, Dict

import httpx


class OpenWeatherClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout_seconds

    async def _get(self, endpoint: str, lat: float, lon: float, units: str) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        params = {"lat": lat, "lon": lon, "units": units, "appid": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()

    async def get_current(self, lat: float, lon: float, units: str) -> Dict[str, Any]:
        return await self._get("weather", lat, lon, units)

    async def get_forecast(self, lat: float, lon: float, units: str) -> Dict[str, Any]:
        # 5 day / 3 hour forecast
        return await self._get("forecast", lat, lon, units)