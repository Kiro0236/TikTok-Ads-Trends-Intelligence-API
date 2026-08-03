"""
Abstract interface for any data provider backing this API.

This is the single seam in the whole system: swap the concrete
implementation returned by `get_data_provider()` (see
`app/core/dependencies.py`) and every router, service and cache layer
keeps working unmodified.

A future concrete implementation should call an AUTHORIZED data
source only — e.g. the official TikTok Business/Marketing API, or a
licensed third-party ads-intelligence data vendor — and translate its
responses into the Raw* domain models below. This class intentionally
knows nothing about HTTP scraping, headers, or fingerprinting; that is
a deliberate boundary, not an oversight.
"""
from abc import ABC, abstractmethod
from datetime import date

from app.models.domain import (
    RawAdDetail,
    RawAdSummary,
    RawHashtagTrend,
    RawSoundTrend,
)


class DataProviderClient(ABC):
    """Contract every data provider implementation must satisfy."""

    @abstractmethod
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
        """Return (items, total_items) for a page of matching ads."""
        raise NotImplementedError

    @abstractmethod
    async def get_ad_details(self, ad_id: str) -> RawAdDetail | None:
        """Return full detail for a single ad, or None if not found."""
        raise NotImplementedError

    @abstractmethod
    async def get_trending_sounds(
        self, *, country_code: str | None, page: int, page_size: int
    ) -> tuple[list[RawSoundTrend], int]:
        raise NotImplementedError

    @abstractmethod
    async def get_trending_hashtags(
        self,
        *,
        country_code: str | None,
        industry_id: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[RawHashtagTrend], int]:
        raise NotImplementedError
