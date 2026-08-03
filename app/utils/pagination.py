"""Shared pagination query-parameter dependency."""
from dataclasses import dataclass

from fastapi import Depends, Query

from app.core.config import Settings, get_settings


@dataclass(slots=True)
class PaginationParams:
    page: int
    page_size: int


def pagination_params(
    page: int = Query(1, ge=1, description="Page number, starting at 1."),
    page_size: int | None = Query(
        None, ge=1, description="Items per page. Defaults to the API default page size."
    ),
    settings: Settings = Depends(get_settings),
) -> PaginationParams:
    resolved_size = page_size or settings.default_page_size
    resolved_size = min(resolved_size, settings.max_page_size)
    return PaginationParams(page=page, page_size=resolved_size)
