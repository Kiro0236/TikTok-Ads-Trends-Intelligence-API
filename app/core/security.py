"""
RapidAPI proxy protection.

RapidAPI forwards every request through its own proxy, which injects the
`X-RapidAPI-Proxy-Secret` header with a value unique to your API. By
verifying that header server-side, we ensure the deployed Vercel URL
cannot be called directly by someone who discovers it — they'd bypass
RapidAPI's billing, quota enforcement and auth entirely otherwise.

Reference: https://docs.rapidapi.com/docs/monetization-through-rapidapi
("Secure your API" — proxy secret verification).
"""
import hmac
import logging

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings

logger = logging.getLogger("tiktok_ads_api.security")


async def verify_rapidapi_proxy_secret(
    x_rapidapi_proxy_secret: str | None = Header(default=None, include_in_schema=False),
    settings: Settings = Depends(get_settings),
) -> None:
    """FastAPI dependency: enforce the RapidAPI proxy secret.

    - If `RAPIDAPI_PROXY_SECRET` is not configured (e.g. local dev),
      enforcement is skipped entirely so the API remains usable without
      a proxy in front of it.
    - If it IS configured, every request must present a matching
      `X-RapidAPI-Proxy-Secret` header, or the request is rejected with
      403 Forbidden before it reaches any router/service code.

    Uses `hmac.compare_digest` for a constant-time comparison to avoid
    leaking timing information about the secret.
    """
    expected = settings.rapidapi_proxy_secret
    if not expected:
        # No secret configured -> protection is off (local/dev mode).
        return

    if not x_rapidapi_proxy_secret or not hmac.compare_digest(
        x_rapidapi_proxy_secret, expected
    ):
        logger.warning("Blocked request missing/invalid X-RapidAPI-Proxy-Secret header.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN_DIRECT_ACCESS",
                    "message": (
                        "Direct access to this API is not allowed. "
                        "Please call it through RapidAPI."
                    ),
                    "details": {},
                }
            },
        )
