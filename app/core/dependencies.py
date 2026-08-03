"""
Dependency-injection wiring.

This is the ONE place that decides which concrete `DataProviderClient`
implementation is used, based on `settings.data_provider_mode`
("mock" or "live"). Every router/service depends on `get_data_provider()`
rather than importing a concrete client directly.
"""
import logging
from functools import lru_cache

from fastapi import Depends

from app.cache.redis_client import RedisCacheClient
from app.clients.base_client import DataProviderClient
from app.clients.live_provider_client import LiveDataProviderClient
from app.clients.mock_provider_client import MockDataProviderClient
from app.core.config import Settings, get_settings

logger = logging.getLogger("tiktok_ads_api.dependencies")


@lru_cache
def _mock_provider_singleton() -> MockDataProviderClient:
    return MockDataProviderClient()


_live_provider_instance: LiveDataProviderClient | None = None


def _live_provider_singleton(settings: Settings) -> LiveDataProviderClient:
    global _live_provider_instance
    if _live_provider_instance is None:
        _live_provider_instance = LiveDataProviderClient(settings)
    return _live_provider_instance


def get_data_provider(settings: Settings = Depends(get_settings)) -> DataProviderClient:
    """Single seam deciding which DataProviderClient implementation is active.

    - `DATA_PROVIDER_MODE=mock` (default): in-memory realistic sample data.
    - `DATA_PROVIDER_MODE=live`: returns `LiveDataProviderClient`, which is
      currently a stub — its methods raise `NotImplementedError` until an
      authorized data source is wired in (see that file's docstring).
    """
    if settings.data_provider_mode == "live":
        logger.info("Using LiveDataProviderClient (data_provider_mode=live).")
        return _live_provider_singleton(settings)
    return _mock_provider_singleton()


_cache_client_instance: RedisCacheClient | None = None


def get_cache_client(settings: Settings = Depends(get_settings)) -> RedisCacheClient:
    global _cache_client_instance
    if _cache_client_instance is None:
        _cache_client_instance = RedisCacheClient(settings)
    return _cache_client_instance


def get_ads_service(
    provider: DataProviderClient = Depends(get_data_provider),
    cache: RedisCacheClient = Depends(get_cache_client),
    settings: Settings = Depends(get_settings),
):
    from app.services.ads_service import AdsService

    return AdsService(provider=provider, cache=cache, settings=settings)


def get_trends_service(
    provider: DataProviderClient = Depends(get_data_provider),
    cache: RedisCacheClient = Depends(get_cache_client),
    settings: Settings = Depends(get_settings),
):
    from app.services.trends_service import TrendsService

    return TrendsService(provider=provider, cache=cache, settings=settings)

