"""Central place to build every cache key used in the API.

Keeping key construction in one module avoids subtle mismatches
between the key a service writes and the key another part of the
code expects to read.
"""


def ads_search_key(
    country_code: str | None,
    industry_id: str | None,
    keyword: str | None,
    sort_by: str,
    page: int,
    page_size: int,
) -> str:
    return (
        f"ads_search:{country_code or 'any'}:{industry_id or 'any'}:"
        f"{keyword or 'any'}:{sort_by}:{page}:{page_size}"
    )


def ads_details_key(ad_id: str) -> str:
    return f"ads_details:{ad_id}"


def trends_sounds_key(country_code: str | None, page: int, page_size: int) -> str:
    return f"trends_sounds:{country_code or 'any'}:{page}:{page_size}"


def trends_hashtags_key(
    country_code: str | None, industry_id: str | None, page: int, page_size: int
) -> str:
    return f"trends_hashtags:{country_code or 'any'}:{industry_id or 'any'}:{page}:{page_size}"
