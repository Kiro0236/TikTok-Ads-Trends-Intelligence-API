"""
Unit tests for RedisCacheClient, using a mocked HTTP transport that
mimics Upstash's REST API contract (command-array body -> {"result": ...}).

The Upstash host isn't in this environment's network allowlist, so
these tests never hit the real network — they validate the request/
response contract our client relies on.
"""
import json

import httpx
import pytest

from app.cache.redis_client import RedisCacheClient
from app.core.config import Settings


class _FakeUpstash:
    """In-memory stand-in for Upstash's REST API, driven by the same
    command-array JSON body format the real service expects."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.received_commands: list[list[str]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        command = json.loads(request.content)
        self.received_commands.append(command)
        name = command[0].upper()

        if name == "SET":
            _, key, value, ex_flag, ttl = command
            assert ex_flag == "EX"
            self.store[key] = value
            return httpx.Response(200, json={"result": "OK"})

        if name == "GET":
            _, key = command
            return httpx.Response(200, json={"result": self.store.get(key)})

        return httpx.Response(400, json={"error": f"unsupported command {name}"})


@pytest.fixture
def fake_upstash(monkeypatch):
    backend = _FakeUpstash()
    transport = httpx.MockTransport(backend.handler)
    real_async_client = httpx.AsyncClient

    def make_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", make_client)
    return backend


@pytest.fixture
def cache_client() -> RedisCacheClient:
    settings = Settings(
        upstash_redis_rest_url="https://fake-upstash.example.com",
        upstash_redis_rest_token="fake-token",
    )
    return RedisCacheClient(settings)


async def test_set_then_get_roundtrips_the_original_dict(fake_upstash, cache_client):
    """Regression test for the bug where a malformed SET request caused
    Upstash to store the raw request body as the value, and GET would
    then return a mangled list instead of the original payload dict —
    triggering a Pydantic ValidationError downstream."""
    payload = {
        "items": [{"ad_id": "ad_123", "ctr": 3.5}],
        "page": 1,
        "total_items": 1,
    }

    ok = await cache_client.set("some:key", payload, ttl_seconds=3600)
    assert ok is True

    result = await cache_client.get("some:key")
    assert isinstance(result, dict)
    assert result == payload


async def test_get_missing_key_returns_none(fake_upstash, cache_client):
    result = await cache_client.get("does-not-exist")
    assert result is None


async def test_set_sends_command_array_with_string_ttl(fake_upstash, cache_client):
    await cache_client.set("k", {"a": 1}, ttl_seconds=100)
    assert fake_upstash.received_commands[-1] == [
        "SET",
        "k",
        json.dumps({"a": 1}),
        "EX",
        "100",
    ]


async def test_get_sends_command_array(fake_upstash, cache_client):
    await cache_client.get("k")
    assert fake_upstash.received_commands[-1] == ["GET", "k"]


async def test_disabled_when_not_configured():
    settings = Settings(upstash_redis_rest_url=None, upstash_redis_rest_token=None)
    client = RedisCacheClient(settings)
    assert client.enabled is False
    assert await client.get("k") is None
    assert await client.set("k", {"a": 1}, ttl_seconds=60) is False


async def test_get_failure_returns_none_not_raise(monkeypatch, cache_client):
    def broken_handler(request):
        return httpx.Response(500, text="upstream error")

    transport = httpx.MockTransport(broken_handler)
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *a, **kw: real_async_client(*a, **{**kw, "transport": transport}),
    )
    result = await cache_client.get("k")
    assert result is None
