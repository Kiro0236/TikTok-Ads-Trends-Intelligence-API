"""
Business logic for the /ads/* endpoints.

Responsibilities:
- validate/normalize input
- check cache, fall back to provider on miss
- map Raw* domain models -> public Pydantic schemas
- never leak raw provider payloads to the client
"""
from datetime import date

from app.cache.cache_keys import ads_details_key, ads_search_key
from app.cache.redis_client import RedisCacheClient
from app.clients.base_client import DataProviderClient
from app.core.config import Settings
from app.exceptions.errors import AdNotFoundError, InvalidParametersError
from app.models.domain import RawAdDetail, RawAdSummary
from app.schemas.ads import (
    AdDetail,
    AdSummary,
    AdsSearchResponse,
    AdvertiserInfo,
    AudienceInfo,
    CampaignMetadata,
    EngagementMetrics,
    SortBy,
    VideoInfo,
)


def _to_ad_summary(raw: RawAdSummary) -> AdSummary:
    return AdSummary(
        ad_id=raw.ad_id,
        thumbnail_url=raw.thumbnail_url,
        advertiser_name=raw.advertiser_name,
        industry=raw.industry,
        country_code=raw.country_code,
        ctr=raw.ctr,
        impressions=raw.impressions,
        engagement_score=raw.engagement_score,
        popularity_score=raw.popularity_score,
        first_seen=raw.first_seen,
    )


def _to_ad_detail(raw: RawAdDetail) -> AdDetail:
    return AdDetail(
        ad_id=raw.ad_id,
        video_info=VideoInfo(
            duration_seconds=raw.duration_seconds,
            resolution=raw.resolution,
            thumbnail_url=raw.thumbnail_url,
            preview_url=raw.preview_url,
        ),
        advertiser_info=AdvertiserInfo(
            name=raw.advertiser_name,
            industry=raw.industry,
            country_code=raw.country_code,
            account_age_days=raw.account_age_days,
            verified=raw.verified,
        ),
        cta=raw.cta,
        landing_page_url=raw.landing_page_url,
        audience=AudienceInfo(
            age_range=raw.age_range,
            gender_split=raw.gender_split,
            top_locations=raw.top_locations,
            interests=raw.interests,
        ),
        demographics=raw.demographics,
        engagement_metrics=EngagementMetrics(
            ctr=raw.ctr,
            impressions=raw.impressions,
            likes=raw.likes,
            shares=raw.shares,
            comments=raw.comments,
            engagement_score=raw.engagement_score,
        ),
        campaign_metadata=CampaignMetadata(
            first_seen=raw.first_seen,
            last_seen=raw.last_seen,
            active=raw.active,
            estimated_spend_range=raw.estimated_spend_range,
        ),
        retrieved_at=raw.retrieved_at,
    )


class AdsService:
    def __init__(
        self,
        provider: DataProviderClient,
        cache: RedisCacheClient,
        settings: Settings,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._settings = settings

    async def search_ads(
        self,
        *,
        country_code: str | None,
        industry_id: str | None,
        keyword: str | None,
        date_from: date | None,
        date_to: date | None,
        sort_by: SortBy,
        page: int,
        page_size: int,
    ) -> AdsSearchResponse:
        if date_from and date_to and date_from > date_to:
            raise InvalidParametersError(
                "date_from must be earlier than or equal to date_to.",
                {"date_from": str(date_from), "date_to": str(date_to)},
            )
        if page < 1 or page_size < 1 or page_size > self._settings.max_page_size:
            raise InvalidParametersError(
                f"page must be >= 1 and page_size must be between 1 and "
                f"{self._settings.max_page_size}.",
                {"page": page, "page_size": page_size},
            )

        cache_key = ads_search_key(
            country_code, industry_id, keyword, sort_by.value, page, page_size
        )
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return AdsSearchResponse.model_validate(cached)

        raw_items, total_items = await self._provider.search_ads(
            country_code=country_code,
            industry_id=industry_id,
            keyword=keyword,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by.value,
            page=page,
            page_size=page_size,
        )

        total_pages = max(1, (total_items + page_size - 1) // page_size)
        response = AdsSearchResponse(
            items=[_to_ad_summary(r) for r in raw_items],
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )

        await self._cache.set(
            cache_key, response.model_dump(mode="json"), self._settings.cache_ttl_ads_search
        )
        return response

    async def get_ad_details(self, ad_id: str) -> AdDetail:
        if not ad_id or not ad_id.strip():
            raise InvalidParametersError("ad_id is required.")

        cache_key = ads_details_key(ad_id)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return AdDetail.model_validate(cached)

        raw = await self._provider.get_ad_details(ad_id)
        if raw is None:
            raise AdNotFoundError(details={"ad_id": ad_id})

        detail = _to_ad_detail(raw)
        await self._cache.set(
            cache_key, detail.model_dump(mode="json"), self._settings.cache_ttl_ads_details
        )
        return detail
