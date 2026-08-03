"""
Pydantic v2 schemas for the /ads/* endpoints.

These are the STABLE public contract of the API. Regardless of which
data provider sits behind `DataProviderClient`, responses are always
normalized into these shapes.
"""
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SortBy(str, Enum):
    ctr = "ctr"
    impressions = "impressions"
    engagement = "engagement"
    popularity = "popularity"


class AdSummary(BaseModel):
    """A single item in a /ads/search result list."""

    model_config = ConfigDict(from_attributes=True)

    ad_id: str = Field(..., description="Stable unique identifier of the advertisement.")
    thumbnail_url: HttpUrl
    advertiser_name: str
    industry: str
    country_code: str
    ctr: float = Field(..., ge=0, le=100, description="Click-through rate, percentage.")
    impressions: int = Field(..., ge=0)
    engagement_score: float = Field(..., ge=0, le=100)
    popularity_score: float = Field(..., ge=0, le=100)
    first_seen: date


class AdsSearchResponse(BaseModel):
    items: list[AdSummary]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class VideoInfo(BaseModel):
    duration_seconds: int
    resolution: str
    thumbnail_url: HttpUrl
    preview_url: HttpUrl = Field(
        ..., description="Provider-hosted preview stream/link (not a redistributable download)."
    )


class AdvertiserInfo(BaseModel):
    name: str
    industry: str
    country_code: str
    account_age_days: int
    verified: bool


class AudienceInfo(BaseModel):
    age_range: str
    gender_split: dict[str, float]
    top_locations: list[str]
    interests: list[str]


class EngagementMetrics(BaseModel):
    ctr: float
    impressions: int
    likes: int
    shares: int
    comments: int
    engagement_score: float


class CampaignMetadata(BaseModel):
    first_seen: date
    last_seen: date
    active: bool
    estimated_spend_range: str


class AdDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ad_id: str
    video_info: VideoInfo
    advertiser_info: AdvertiserInfo
    cta: str
    landing_page_url: HttpUrl
    audience: AudienceInfo
    demographics: dict[str, float]
    engagement_metrics: EngagementMetrics
    campaign_metadata: CampaignMetadata
    retrieved_at: datetime
