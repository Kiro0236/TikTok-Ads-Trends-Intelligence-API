"""
Mock implementation of `DataProviderClient`.

Generates deterministic, realistic-looking sample data entirely in
Python — no network calls, no external dependencies. This lets the
full API surface (search, details, trends, caching, pagination,
error handling) be exercised and demoed end-to-end before a real,
authorized data source is wired in.

Swap this out by implementing `DataProviderClient` against a real
provider and pointing `get_data_provider()` at it. Nothing else in
the codebase needs to change.
"""
import hashlib
import random
from datetime import date, datetime, timedelta, timezone

from app.clients.base_client import DataProviderClient
from app.models.domain import (
    RawAdDetail,
    RawAdSummary,
    RawHashtagTrend,
    RawSoundTrend,
)

_INDUSTRIES = [
    "Beauty & Personal Care",
    "Fashion & Apparel",
    "Health & Wellness",
    "Home & Garden",
    "Electronics",
    "Food & Beverage",
    "Fitness",
    "Pet Supplies",
    "Toys & Games",
    "Automotive",
]

_COUNTRIES = ["US", "GB", "DE", "FR", "IT", "ES", "BR", "MX", "CA", "AU"]

_ADVERTISER_NAME_PARTS = [
    "Nova", "Lumen", "Pulse", "Verve", "Zenith", "Aster", "Orbit", "Kinetic",
    "Bloom", "Vivid", "Crestline", "Solace", "Amberly", "Northfield", "Halcyon",
]
_ADVERTISER_SUFFIXES = ["Co", "Studio", "Labs", "Goods", "Collective", "Brands", "Direct"]

_CTA_OPTIONS = ["Shop Now", "Learn More", "Sign Up", "Get Offer", "Download", "Watch More"]

_SOUND_TITLES = [
    "Neon Nights", "Sunset Drift", "Golden Hour Vibes", "Midnight Bloom",
    "Electric Pulse", "Velvet Skies", "Paper Planes (Remix)", "Ocean Static",
    "City Lights Loop", "Warm Static", "Slow Motion", "Afterglow",
]
_ARTISTS = [
    "Kali Vance", "Theo Marsh", "Nadia Wren", "Milo Frost", "Ezra Lane",
    "Wren Delacroix", "Sable & Co.", "June Harlow",
]

_HASHTAG_WORDS = [
    "cleanbeauty", "tiktokmademebuyit", "fitcheck", "skincareroutine",
    "smallbusiness", "petsoftiktok", "homeorganization", "techgadgets",
    "summerstyle", "budgetfinds", "kitchenhacks", "workoutmotivation",
]
_CATEGORIES = ["Beauty", "Fashion", "Lifestyle", "Tech", "Fitness", "Home", "Food"]


def _seeded_random(*parts: str) -> random.Random:
    """Deterministic RNG per unique key, so repeated calls with the
    same params return stable-looking (but still varied) mock data."""
    seed = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return random.Random(seed)


def _make_advertiser_name(rng: random.Random) -> str:
    return f"{rng.choice(_ADVERTISER_NAME_PARTS)} {rng.choice(_ADVERTISER_SUFFIXES)}"


def _make_ad_summary(rng: random.Random, index: int, country_code: str, industry: str) -> RawAdSummary:
    ad_id = f"ad_{rng.randint(10**9, 10**10 - 1)}"
    impressions = rng.randint(50_000, 15_000_000)
    ctr = round(rng.uniform(0.5, 12.0), 2)
    engagement_score = round(rng.uniform(20, 99), 1)
    popularity_score = round(rng.uniform(20, 99), 1)
    first_seen = date.today() - timedelta(days=rng.randint(1, 180))
    return RawAdSummary(
        ad_id=ad_id,
        thumbnail_url=f"https://picsum.photos/seed/{ad_id}/400/700",
        advertiser_name=_make_advertiser_name(rng),
        industry=industry,
        country_code=country_code,
        ctr=ctr,
        impressions=impressions,
        engagement_score=engagement_score,
        popularity_score=popularity_score,
        first_seen=first_seen,
    )


class MockDataProviderClient(DataProviderClient):
    """In-memory, deterministic mock provider. No external calls."""

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
        country = country_code or "US"
        industry = industry_id or rng_choice_industry(country, keyword)

        rng = _seeded_random("search", country, industry, keyword or "", sort_by)
        total_items = rng.randint(120, 480)

        all_items = [
            _make_ad_summary(
                _seeded_random("search", country, industry, keyword or "", str(i)),
                i,
                country,
                industry,
            )
            for i in range(total_items)
        ]

        sort_key_map = {
            "ctr": lambda a: a.ctr,
            "impressions": lambda a: a.impressions,
            "engagement": lambda a: a.engagement_score,
            "popularity": lambda a: a.popularity_score,
        }
        key_fn = sort_key_map.get(sort_by, sort_key_map["popularity"])
        all_items.sort(key=key_fn, reverse=True)

        start = (page - 1) * page_size
        end = start + page_size
        return all_items[start:end], total_items

    async def get_ad_details(self, ad_id: str) -> RawAdDetail | None:
        if not ad_id.startswith("ad_"):
            return None

        rng = _seeded_random("details", ad_id)
        industry = rng.choice(_INDUSTRIES)
        country = rng.choice(_COUNTRIES)
        first_seen = date.today() - timedelta(days=rng.randint(30, 200))
        last_seen = first_seen + timedelta(days=rng.randint(5, 60))
        impressions = rng.randint(50_000, 15_000_000)
        likes = int(impressions * rng.uniform(0.02, 0.12))
        shares = int(likes * rng.uniform(0.05, 0.3))
        comments = int(likes * rng.uniform(0.02, 0.15))

        return RawAdDetail(
            ad_id=ad_id,
            duration_seconds=rng.randint(9, 60),
            resolution="1080x1920",
            thumbnail_url=f"https://picsum.photos/seed/{ad_id}-thumb/400/700",
            preview_url=f"https://provider.example.com/preview/{ad_id}",
            advertiser_name=_make_advertiser_name(rng),
            industry=industry,
            country_code=country,
            account_age_days=rng.randint(60, 2500),
            verified=rng.random() > 0.5,
            cta=rng.choice(_CTA_OPTIONS),
            landing_page_url=f"https://shop.example.com/products/{ad_id}",
            age_range=rng.choice(["18-24", "25-34", "35-44", "18-34", "25-44"]),
            gender_split={"female": round(rng.uniform(0.3, 0.7), 2), "male": 0.0},
            top_locations=rng.sample(
                ["New York", "Los Angeles", "London", "Berlin", "Paris", "São Paulo", "Toronto"],
                k=3,
            ),
            interests=rng.sample(
                ["beauty", "fashion", "fitness", "tech", "home decor", "cooking", "travel", "gaming"],
                k=4,
            ),
            demographics={
                "13-17": round(rng.uniform(0, 0.1), 2),
                "18-24": round(rng.uniform(0.15, 0.4), 2),
                "25-34": round(rng.uniform(0.2, 0.4), 2),
                "35-44": round(rng.uniform(0.1, 0.25), 2),
                "45+": round(rng.uniform(0.05, 0.2), 2),
            },
            ctr=round(rng.uniform(0.5, 12.0), 2),
            impressions=impressions,
            likes=likes,
            shares=shares,
            comments=comments,
            engagement_score=round(rng.uniform(20, 99), 1),
            first_seen=first_seen,
            last_seen=last_seen,
            active=rng.random() > 0.3,
            estimated_spend_range=rng.choice(
                ["$1K-$5K", "$5K-$20K", "$20K-$50K", "$50K-$100K", "$100K+"]
            ),
            retrieved_at=datetime.now(timezone.utc),
        )

    async def get_trending_sounds(
        self, *, country_code: str | None, page: int, page_size: int
    ) -> tuple[list[RawSoundTrend], int]:
        country = country_code or "US"
        rng = _seeded_random("sounds", country)
        total_items = rng.randint(60, 150)

        all_items = []
        for i in range(total_items):
            item_rng = _seeded_random("sounds", country, str(i))
            all_items.append(
                RawSoundTrend(
                    sound_id=f"snd_{item_rng.randint(10**8, 10**9 - 1)}",
                    name=item_rng.choice(_SOUND_TITLES),
                    author=item_rng.choice(_ARTISTS),
                    usage_count=item_rng.randint(1_000, 900_000),
                    popularity_score=round(item_rng.uniform(30, 99), 1),
                    trend_score=round(item_rng.uniform(30, 99), 1),
                    country_code=country,
                )
            )

        all_items.sort(key=lambda s: s.trend_score, reverse=True)
        start = (page - 1) * page_size
        end = start + page_size
        return all_items[start:end], total_items

    async def get_trending_hashtags(
        self,
        *,
        country_code: str | None,
        industry_id: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[RawHashtagTrend], int]:
        country = country_code or "US"
        industry = industry_id or "General"
        rng = _seeded_random("hashtags", country, industry)
        total_items = rng.randint(40, 100)

        all_items = []
        for i in range(total_items):
            item_rng = _seeded_random("hashtags", country, industry, str(i))
            all_items.append(
                RawHashtagTrend(
                    hashtag=f"#{item_rng.choice(_HASHTAG_WORDS)}{item_rng.randint(1, 99)}",
                    category=item_rng.choice(_CATEGORIES),
                    popularity_score=round(item_rng.uniform(30, 99), 1),
                    industry_relation=industry,
                    country_code=country,
                    video_count=item_rng.randint(500, 2_000_000),
                )
            )

        all_items.sort(key=lambda h: h.popularity_score, reverse=True)
        start = (page - 1) * page_size
        end = start + page_size
        return all_items[start:end], total_items


def rng_choice_industry(country: str, keyword: str | None) -> str:
    rng = _seeded_random("industry-fallback", country, keyword or "")
    return rng.choice(_INDUSTRIES)
