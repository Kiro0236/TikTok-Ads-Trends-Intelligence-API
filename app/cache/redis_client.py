"""
Thin async wrapper around Upstash Redis' REST API.

Using the REST API (instead of a raw TCP redis client) is deliberate:
it works from serverless/edge runtimes like Vercel functions without
persistent connections.

Design choice: cache failures must never break a request. Every
public method catches its own errors and returns None / False on
failure, logging a warning. Callers (services) always have a
"fetch live" fallback path.
"""
import json
import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger("tiktok_ads_api.cache")


class RedisCacheClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.upstash_redis_rest_url
        self._token = settings.upstash_redis_rest_token
        self._enabled = bool(self._base_url and self._token)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    async def get(self, key: str) -> Any | None:
        if not self._enabled:
            return None
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self._base_url}/get/{key}", headers=self._headers())
                resp.raise_for_status()
                payload = resp.json()
                raw = payload.get("result")
                if raw is None:
                    return None
                return json.loads(raw)
        except Exception as exc:  # noqa: BLE001 - cache must never raise upstream
            logger.warning("Cache GET failed for key=%s: %s", key, exc)
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        if not self._enabled:
            return False
        try:
            serialized = json.dumps(value, default=str)
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(
                    f"{self._base_url}/set/{key}",
                    headers=self._headers(),
                    json=[serialized, "EX", ttl_seconds],
                )
                resp.raise_for_status()
                return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache SET failed for key=%s: %s", key, exc)
            return False
