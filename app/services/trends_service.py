"""Business logic for the /trends/* endpoints."""
from app.cache.cache_keys import trends_hashtags_key, trends_sounds_key
from app.cache.redis_client import RedisCacheClient
from app.clients.base_client import DataProviderClient
from app.core.config import Settings
from app.exceptions.errors import InvalidParametersError
from app.models.domain import RawHashtagTrend, RawSoundTrend
from app.schemas.trends import (
    HashtagsTrendResponse,
    HashtagTrend,
    SoundsTrendResponse,
    SoundTrend,
)


def _to_sound_trend(raw: RawSoundTrend) -> SoundTrend:
    return SoundTrend(
        sound_id=raw.sound_id,
        name=raw.name,
        author=raw.author,
        usage_count=raw.usage_count,
        popularity_score=raw.popularity_score,
        trend_score=raw.trend_score,
        country_code=raw.country_code,
    )


def _to_hashtag_trend(raw: RawHashtagTrend) -> HashtagTrend:
    return HashtagTrend(
        hashtag=raw.hashtag,
        category=raw.category,
        popularity_score=raw.popularity_score,
        industry_relation=raw.industry_relation,
        country_code=raw.country_code,
        video_count=raw.video_count,
    )


class TrendsService:
    def __init__(
        self,
        provider: DataProviderClient,
        cache: RedisCacheClient,
        settings: Settings,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._settings = settings

    def _validate_pagination(self, page: int, page_size: int) -> None:
        if page < 1 or page_size < 1 or page_size > self._settings.max_page_size:
            raise InvalidParametersError(
                f"page must be >= 1 and page_size must be between 1 and "
                f"{self._settings.max_page_size}.",
                {"page": page, "page_size": page_size},
            )

    async def get_trending_sounds(
        self, *, country_code: str | None, page: int, page_size: int
    ) -> SoundsTrendResponse:
        self._validate_pagination(page, page_size)

        cache_key = trends_sounds_key(country_code, page, page_size)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return SoundsTrendResponse.model_validate(cached)

        raw_items, total_items = await self._provider.get_trending_sounds(
            country_code=country_code, page=page, page_size=page_size
        )
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        response = SoundsTrendResponse(
            items=[_to_sound_trend(r) for r in raw_items],
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
        await self._cache.set(
            cache_key, response.model_dump(mode="json"), self._settings.cache_ttl_trends_sounds
        )
        return response

    async def get_trending_hashtags(
        self,
        *,
        country_code: str | None,
        industry_id: str | None,
        page: int,
        page_size: int,
    ) -> HashtagsTrendResponse:
        self._validate_pagination(page, page_size)

        cache_key = trends_hashtags_key(country_code, industry_id, page, page_size)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return HashtagsTrendResponse.model_validate(cached)

        raw_items, total_items = await self._provider.get_trending_hashtags(
            country_code=country_code,
            industry_id=industry_id,
            page=page,
            page_size=page_size,
        )
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        response = HashtagsTrendResponse(
            items=[_to_hashtag_trend(r) for r in raw_items],
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
        await self._cache.set(
            cache_key,
            response.model_dump(mode="json"),
            self._settings.cache_ttl_trends_hashtags,
        )
        return response
