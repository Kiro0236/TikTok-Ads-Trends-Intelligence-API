"""
Application configuration.

All settings are loaded from environment variables. No secrets are
hardcoded anywhere in the codebase. See `.env.example` for the full
list of required/optional variables.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---
    app_name: str = "TikTok Ads Intelligence API"
    app_env: Literal["development", "staging", "production"] = "development"
    api_version: str = "v1"
    debug: bool = False

    # --- Data provider ---
    # "mock" returns realistic fake data (default, safe to run out of the box).
    # "live" is a placeholder for a future authorized data provider
    # (official TikTok Business API, or a licensed third-party vendor).
    data_provider_mode: Literal["mock", "live"] = "mock"
    data_provider_api_key: str | None = Field(default=None)
    data_provider_base_url: str | None = Field(default=None)

    # --- Redis (Upstash) ---
    upstash_redis_rest_url: str | None = Field(default=None)
    upstash_redis_rest_token: str | None = Field(default=None)

    # --- Cache TTLs (seconds) ---
    cache_ttl_ads_search: int = 12 * 60 * 60       # 12h
    cache_ttl_ads_details: int = 12 * 60 * 60      # 12h
    cache_ttl_trends_sounds: int = 24 * 60 * 60    # 24h
    cache_ttl_trends_hashtags: int = 24 * 60 * 60  # 24h

    # --- Pagination defaults ---
    default_page_size: int = 20
    max_page_size: int = 50

    # --- Rate limiting (ready for future enforcement, e.g. via RapidAPI or middleware) ---
    rate_limit_enabled: bool = False
    rate_limit_requests_per_minute: int = 60

    # --- Apify (generic platform client) ---
    # Only the auth token lives here. Which Actor(s) to call, and for what
    # data, is a decision made explicitly at the call site (e.g. in a
    # DataProviderClient implementation) against a source you've verified
    # is authorized to use — never assumed by this generic client.
    apify_api_token: str | None = Field(default=None)

    # --- RapidAPI proxy protection ---
    # When set, every request must carry a matching X-RapidAPI-Proxy-Secret
    # header, so the deployed Vercel URL can't be called directly, bypassing
    # RapidAPI's billing/auth layer. Left unset (None) in local/dev mode,
    # enforcement is skipped so you can hit the API without a proxy in front.
    rapidapi_proxy_secret: str | None = Field(default=None)


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor, used as a FastAPI dependency."""
    return Settings()
