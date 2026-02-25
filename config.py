from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "weather-api"
    log_level: str = "INFO"

    # Provider
    openweather_api_key: str
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Cache tuning
    cache_ttl_current_seconds: int = 120
    cache_ttl_forecast_seconds: int = 900
    cache_coord_round_decimals: int = 2


settings = Settings()