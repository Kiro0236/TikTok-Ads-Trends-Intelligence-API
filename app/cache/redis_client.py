"""
Thin async wrapper around Upstash Redis' REST API.

Using the REST API (instead of a raw TCP redis client) is deliberate:
it works from serverless/edge runtimes like Vercel functions without
persistent connections.

Request format: Upstash's REST API supports two styles — a path-style
URL (`/set/<key>` with the value as the raw body, extra Redis command
options passed as query params), and a "command array" style, POSTed
to the base URL as a JSON array mirroring the raw Redis command, e.g.
`["SET", key, value, "EX", ttl]`. We use the command-array style
throughout, since Upstash's own docs recommend it specifically for
JSON payloads — it avoids the ambiguity the path-style form has when
POSTing a body (an earlier version of this file mixed the two styles,
which caused Upstash to store the literal request body as the cached
value instead of just the intended payload).

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

    async def _run_command(self, command: list[str]) -> Any:
        """POST a single Redis command (as a JSON array) to Upstash's REST
        API and return the parsed `result` field, or None if the command
        failed or the endpoint returned no result."""
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                self._base_url, headers=self._headers(), json=command
            )
            resp.raise_for_status()
            payload = resp.json()
            return payload.get("result")

    async def get(self, key: str) -> Any | None:
        if not self._enabled:
            return None
        try:
            raw = await self._run_command(["GET", key])
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
            result = await self._run_command(
                ["SET", key, serialized, "EX", str(ttl_seconds)]
            )
            return result == "OK"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache SET failed for key=%s: %s", key, exc)
            return False
