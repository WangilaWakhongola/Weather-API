from typing import Literal, Optional
from pydantic import BaseModel, Field


Units = Literal["metric", "imperial"]


class Location(BaseModel):
    lat: float
    lon: float
    name: Optional[str] = None
    country: Optional[str] = None


class CacheInfo(BaseModel):
    hit: bool
    age_seconds: Optional[int] = None
    stale: bool = False


class ProviderInfo(BaseModel):
    name: str = "openweather"
    data_timestamp: Optional[int] = None


class CurrentWeatherResponse(BaseModel):
    location: Location
    units: Units
    observed_at: Optional[str] = None
    current: dict = Field(default_factory=dict)
    provider: ProviderInfo = Field(default_factory=ProviderInfo)
    cache: CacheInfo


class ForecastResponse(BaseModel):
    location: Location
    units: Units
    forecast: dict = Field(default_factory=dict)
    provider: ProviderInfo = Field(default_factory=ProviderInfo)
    cache: CacheInfo
