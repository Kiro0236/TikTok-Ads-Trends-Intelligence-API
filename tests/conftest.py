"""
Shared pytest fixtures.

Key detail: `get_settings()` is `lru_cache`-d (see app/core/config.py),
so tests that need a different environment (e.g. with/without
RAPIDAPI_PROXY_SECRET configured) must clear that cache after changing
`os.environ`, or FastAPI will keep serving the previously cached
Settings instance to every request.
"""
import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Ensure every test starts with a fresh, env-accurate Settings object,
    and that no test leaks its env changes into the next one."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    """Client for the default local/dev setup: DATA_PROVIDER_MODE=mock,
    RAPIDAPI_PROXY_SECRET unset (so the proxy-secret check is a no-op)."""
    os.environ.pop("RAPIDAPI_PROXY_SECRET", None)
    os.environ["DATA_PROVIDER_MODE"] = "mock"
    get_settings.cache_clear()
    return TestClient(app)


@pytest.fixture
def client_with_proxy_secret() -> tuple[TestClient, str]:
    """Client with RAPIDAPI_PROXY_SECRET configured, to exercise the
    security dependency's enforcement path. Returns (client, secret)."""
    secret = "test-secret-abc123"
    os.environ["RAPIDAPI_PROXY_SECRET"] = secret
    os.environ["DATA_PROVIDER_MODE"] = "mock"
    get_settings.cache_clear()
    return TestClient(app), secret
