"""
Internal domain dataclasses.

These represent data as fetched from a provider BEFORE normalization
into the public API schemas (app/schemas). Keeping this separation
means a future provider integration only has to produce these shapes;
the mapping into public response schemas stays untouched.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timezone


@dataclass(slots=True)
class RawAdSummary:
    ad_id: str
    thumbnail_url: str
    advertiser_name: str
    industry: str
    country_code: str
    ctr: float
    impressions: int
    engagement_score: float
    popularity_score: float
    first_seen: date


@dataclass(slots=True)
class RawAdDetail:
    ad_id: str
    duration_seconds: int
    resolution: str
    thumbnail_url: str
    preview_url: str
    advertiser_name: str
    industry: str
    country_code: str
    account_age_days: int
    verified: bool
    cta: str
    landing_page_url: str
    age_range: str
    gender_split: dict[str, float]
    top_locations: list[str]
    interests: list[str]
    demographics: dict[str, float]
    ctr: float
    impressions: int
    likes: int
    shares: int
    comments: int
    engagement_score: float
    first_seen: date
    last_seen: date
    active: bool
    estimated_spend_range: str
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class RawSoundTrend:
    sound_id: str
    name: str
    author: str
    usage_count: int
    popularity_score: float
    trend_score: float
    country_code: str


@dataclass(slots=True)
class RawHashtagTrend:
    hashtag: str
    category: str
    popularity_score: float
    industry_relation: str
    country_code: str
    video_count: int
