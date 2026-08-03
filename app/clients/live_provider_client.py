"""
Live data provider — STUB.

This class is the seam where a real, authorized data source gets wired
in (e.g. the official TikTok Business/Marketing API, or a licensed
third-party ads-intelligence vendor). It intentionally does NOT contain
any scraping, header-spoofing, or browser-fingerprinting logic — that
boundary is deliberate, not an oversight.

Every method currently raises `NotImplementedError` and logs a
placeholder warning. To go live:

1. Pick an authorized data source (see README.md, section
   "Going live with real data").
2. Implement each method below using `self._http_client` (or your SDK
   of choice) to call that source, and map its response into the
   `Raw*` domain models from `app.models.domain` — the SAME shapes the
   mock provider already returns, so no other layer of the app needs
   to change.
3. Set `DATA_PROVIDER_MODE=live` and the relevant `DATA_PROVIDER_*` /
   provider-specific env vars.

`app/core/dependencies.py::get_data_provider` already instantiates
this class automatically when `DATA_PROVIDER_MODE=live`.
"""
import logging
from datetime import date

from app.clients.base_client import DataProviderClient
from app.core.config import Settings
from app.models.domain import (
    RawAdDetail,
    RawAdSummary,
    RawHashtagTrend,
    RawSoundTrend,
)

logger = logging.getLogger("tiktok_ads_api.live_provider")


class LiveDataProviderClient(DataProviderClient):
    """Placeholder implementation backed by a real, authorized data source.

    Not yet implemented. Every method logs a warning and raises
    `NotImplementedError`, wrapped by the caller into a clean
    `ProviderUnavailableError` (502) so the API still fails gracefully
    instead of crashing with a raw traceback.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.data_provider_base_url
        self._api_key = settings.data_provider_api_key
        # TODO: initialize your real HTTP client / SDK here, e.g.:
        # self._http_client = httpx.AsyncClient(
        #     base_url=self._base_url,
        #     headers={"Authorization": f"Bearer {self._api_key}"},
        #     timeout=10.0,
        # )

    def _not_implemented(self, method_name: str) -> None:
        logger.warning(
            "[LiveDataProviderClient] '%s' called but no live data source is "
            "wired in yet. Implement this method against an authorized "
            "provider (see app/clients/live_provider_client.py docstring).",
            method_name,
        )
        raise NotImplementedError(
            f"LiveDataProviderClient.{method_name} is not implemented yet. "
            "Wire it up against an authorized data source."
        )

    async def search_ads(
        self,
        *,
        country_code: str | None,
        industry_id: str | None,
        keyword: str | None,
        date_from: date | None,
        date_to: date | None,
        sort_by: str,
        page: int,
        page_size: int,
    ) -> tuple[list[RawAdSummary], int]:
        # TODO: call the real provider, e.g.:
        # resp = await self._http_client.get("/ads/search", params={...})
        # resp.raise_for_status()
        # return _map_to_raw_ad_summaries(resp.json()), resp.json()["total"]
        self._not_implemented("search_ads")

    async def get_ad_details(self, ad_id: str) -> RawAdDetail | None:
        # TODO: call the real provider and map its response to RawAdDetail,
        # or return None if the provider reports the ad doesn't exist.
        self._not_implemented("get_ad_details")

    async def get_trending_sounds(
        self, *, country_code: str | None, page: int, page_size: int
    ) -> tuple[list[RawSoundTrend], int]:
        # TODO: call the real provider's trending-sounds endpoint.
        self._not_implemented("get_trending_sounds")

    async def get_trending_hashtags(
        self,
        *,
        country_code: str | None,
        industry_id: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[RawHashtagTrend], int]:
        # TODO: call the real provider's trending-hashtags endpoint.
        self._not_implemented("get_trending_hashtags")
