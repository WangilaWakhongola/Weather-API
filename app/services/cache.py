import json
import time
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import redis


@dataclass
class CacheResult:
    value: Optional[dict]
    hit: bool
    age_seconds: Optional[int]
    stale: bool


class RedisCache:
    """
    Stores JSON payload + metadata:
      key -> {"stored_at": <unix>, "payload": {...}}
    """

    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url, decode_responses=True)

    def get_json(self, key: str, allow_stale: bool = True) -> CacheResult:
        raw = self.client.get(key)
        if not raw:
            return CacheResult(value=None, hit=False, age_seconds=None, stale=False)

        try:
            obj = json.loads(raw)
            stored_at = int(obj.get("stored_at", 0))
            payload = obj.get("payload")
            age = max(0, int(time.time()) - stored_at)
            return CacheResult(value=payload, hit=True, age_seconds=age, stale=False)
        except Exception:
            return CacheResult(value=None, hit=False, age_seconds=None, stale=False)

    def set_json(self, key: str, payload: dict, ttl_seconds: int) -> None:
        obj = {"stored_at": int(time.time()), "payload": payload}
        self.client.setex(key, ttl_seconds, json.dumps(obj))

    def acquire_lock(self, lock_key: str, ttl_ms: int = 10_000) -> bool:
        return bool(self.client.set(lock_key, "1", nx=True, px=ttl_ms))

    def release_lock(self, lock_key: str) -> None:
        try:
            self.client.delete(lock_key)
        except Exception:
            pass


def rounded_coords(lat: float, lon: float, decimals: int) -> Tuple[float, float]:
    return (round(lat, decimals), round(lon, decimals))
