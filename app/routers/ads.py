"""Endpoints: GET /ads/search, GET /ads/details."""
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_ads_service
from app.core.security import verify_rapidapi_proxy_secret
from app.schemas.ads import AdDetail, AdsSearchResponse, SortBy
from app.services.ads_service import AdsService
from app.utils.pagination import PaginationParams, pagination_params
from app.utils.query_params import normalize_optional_str

router = APIRouter(
    prefix="/ads",
    tags=["Ads"],
    dependencies=[Depends(verify_rapidapi_proxy_secret)],
)


@router.get(
    "/search",
    response_model=AdsSearchResponse,
    summary="Search top-performing TikTok advertisements",
    description=(
        "Find winning TikTok ad creatives, pre-filtered and sorted by "
        "performance signals such as CTR, impressions, engagement or "
        "overall popularity. Returns clean, normalized JSON — never raw "
        "provider payloads."
    ),
)
async def search_ads(
    country_code: str | None = Query(
        None,
        examples=["US"],
        description="Two-letter country code (e.g. 'US'). Extra whitespace, "
        "quotes, or array-wrapping from the calling client are tolerated "
        "and cleaned up automatically.",
    ),
    industry_id: str | None = Query(None, examples=["Beauty & Personal Care"]),
    keyword: str | None = Query(None, examples=["skincare"]),
    date_from: date | None = Query(None, description="Inclusive start of the date range."),
    date_to: date | None = Query(None, description="Inclusive end of the date range."),
    sort_by: SortBy = Query(SortBy.popularity),
    pagination: PaginationParams = Depends(pagination_params),
    service: AdsService = Depends(get_ads_service),
) -> AdsSearchResponse:
    country_code = normalize_optional_str(country_code)
    if country_code:
        # Tolerate a client sending more than 2 characters (e.g. stray
        # wrapping we couldn't fully unwrap) by taking a safe, well-formed
        # value instead of hard-failing the request.
        country_code = country_code.upper()[:2]

    return await service.search_ads(
        country_code=country_code,
        industry_id=normalize_optional_str(industry_id),
        keyword=normalize_optional_str(keyword),
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/details",
    response_model=AdDetail,
    summary="Get a full competitor campaign intelligence report",
    description=(
        "Returns a complete breakdown of a single advertisement: video "
        "info, advertiser info, CTA, landing page, audience and "
        "demographic data, engagement metrics and campaign metadata."
    ),
)
async def get_ad_details(
    ad_id: str = Query(..., examples=["ad_1234567890"]),
    service: AdsService = Depends(get_ads_service),
) -> AdDetail:
    normalized_id = normalize_optional_str(ad_id) or ad_id
    return await service.get_ad_details(normalized_id)

