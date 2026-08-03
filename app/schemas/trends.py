"""Pydantic v2 schemas for the /trends/* endpoints."""
from pydantic import BaseModel, ConfigDict, Field


class SoundTrend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sound_id: str
    name: str
    author: str
    usage_count: int = Field(..., ge=0)
    popularity_score: float = Field(..., ge=0, le=100)
    trend_score: float = Field(..., ge=0, le=100)
    country_code: str


class SoundsTrendResponse(BaseModel):
    items: list[SoundTrend]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class HashtagTrend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hashtag: str
    category: str
    popularity_score: float = Field(..., ge=0, le=100)
    industry_relation: str
    country_code: str
    video_count: int = Field(..., ge=0)


class HashtagsTrendResponse(BaseModel):
    items: list[HashtagTrend]
    page: int
    page_size: int
    total_items: int
    total_pages: int
