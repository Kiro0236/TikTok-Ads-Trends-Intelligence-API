"""Endpoints: GET /trends/sounds, GET /trends/hashtags."""
from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_trends_service
from app.core.security import verify_rapidapi_proxy_secret
from app.schemas.trends import HashtagsTrendResponse, SoundsTrendResponse
from app.services.trends_service import TrendsService
from app.utils.pagination import PaginationParams, pagination_params

router = APIRouter(
    prefix="/trends",
    tags=["Trends"],
    dependencies=[Depends(verify_rapidapi_proxy_secret)],
)


@router.get(
    "/sounds",
    response_model=SoundsTrendResponse,
    summary="Get trending TikTok sounds",
    description=(
        "Returns trending audio tracks with usage and popularity "
        "metrics. Aggressively cached (24h TTL) since sound trends "
        "change slowly."
    ),
)
async def get_trending_sounds(
    country_code: str | None = Query(None, min_length=2, max_length=2, examples=["US"]),
    pagination: PaginationParams = Depends(pagination_params),
    service: TrendsService = Depends(get_trends_service),
) -> SoundsTrendResponse:
    return await service.get_trending_sounds(
        country_code=country_code, page=pagination.page, page_size=pagination.page_size
    )


@router.get(
    "/hashtags",
    response_model=HashtagsTrendResponse,
    summary="Get trending TikTok hashtags",
    description=(
        "Returns trending hashtags with category and industry "
        "relevance. Optimized for low latency via caching."
    ),
)
async def get_trending_hashtags(
    country_code: str | None = Query(None, min_length=2, max_length=2, examples=["US"]),
    industry_id: str | None = Query(None, examples=["Fashion & Apparel"]),
    pagination: PaginationParams = Depends(pagination_params),
    service: TrendsService = Depends(get_trends_service),
) -> HashtagsTrendResponse:
    return await service.get_trending_hashtags(
        country_code=country_code,
        industry_id=industry_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
