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
    country_code: str | None = Query(...),
    industry_id: str | None = Query(...),
    keyword: str | None = Query(...),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    sort_by: SortBy = Query(SortBy.popularity),
    pagination: PaginationParams = Depends(pagination_params),
    service: AdsService = Depends(get_ads_service),
) -> AdsSearchResponse:
    # 1. Normalizzazione
    clean_country = normalize_optional_str(country_code)
    if clean_country:
        clean_country = clean_country.upper()[:2]

    clean_industry = normalize_optional_str(industry_id)
    clean_keyword = normalize_optional_str(keyword)

    # 2. Fallback "any" se sono None (EVITA L'ERRORE 500)
    final_country = clean_country or "any"
    final_industry = clean_industry or "any"
    final_keyword = clean_keyword or "any"

    return await service.search_ads(
        country_code=final_country,
        industry_id=final_industry,
        keyword=final_keyword,
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

