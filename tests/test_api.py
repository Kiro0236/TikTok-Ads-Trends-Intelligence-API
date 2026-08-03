"""
End-to-end API tests, run against the app in-process (no live server
needed) via Starlette's TestClient.

Covers:
- every endpoint returns 200 in mock mode with a well-formed body
- the X-RapidAPI-Proxy-Secret dependency blocks requests correctly
  when a secret is configured, and gets out of the way when it isn't
"""


# ---------------------------------------------------------------------------
# Endpoint happy-path tests (mock mode, no proxy secret configured)
# ---------------------------------------------------------------------------


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["provider_mode"] == "mock"


def test_ads_search_returns_200_with_expected_shape(client):
    resp = client.get("/ads/search", params={"country_code": "US", "page_size": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body and "total_items" in body and "page" in body
    assert len(body["items"]) <= 5
    if body["items"]:
        first = body["items"][0]
        for field in ("ad_id", "advertiser_name", "ctr", "impressions"):
            assert field in first


def test_ads_search_default_params_returns_200(client):
    resp = client.get("/ads/search")
    assert resp.status_code == 200


def test_ads_search_invalid_page_size_is_clamped_not_error(client):
    resp = client.get("/ads/search", params={"page_size": 999})
    assert resp.status_code == 200
    assert resp.json()["page_size"] <= 50


def test_ads_search_invalid_date_range_returns_422(client):
    resp = client.get(
        "/ads/search",
        params={"date_from": "2026-06-01", "date_to": "2026-01-01"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_PARAMETERS"


def test_ads_details_returns_200_with_expected_shape(client):
    resp = client.get("/ads/details", params={"ad_id": "ad_1234567890"})
    assert resp.status_code == 200
    body = resp.json()
    for field in (
        "ad_id",
        "video_info",
        "advertiser_info",
        "cta",
        "landing_page_url",
        "audience",
        "engagement_metrics",
        "campaign_metadata",
    ):
        assert field in body


def test_ads_details_not_found_returns_404(client):
    resp = client.get("/ads/details", params={"ad_id": "not-a-real-ad"})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "AD_NOT_FOUND"


def test_trends_sounds_returns_200_with_expected_shape(client):
    resp = client.get("/trends/sounds", params={"country_code": "US"})
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    if body["items"]:
        for field in ("sound_id", "name", "author", "trend_score"):
            assert field in body["items"][0]


def test_trends_hashtags_returns_200_with_expected_shape(client):
    resp = client.get(
        "/trends/hashtags", params={"country_code": "US", "industry_id": "Fashion"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    if body["items"]:
        for field in ("hashtag", "category", "popularity_score"):
            assert field in body["items"][0]


def test_docs_and_openapi_are_served(client):
    assert client.get("/docs").status_code == 200
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert set(spec["paths"].keys()) == {
        "/ads/search",
        "/ads/details",
        "/trends/sounds",
        "/trends/hashtags",
        "/health",
    }


# ---------------------------------------------------------------------------
# RapidAPI proxy-secret security tests
# ---------------------------------------------------------------------------


def test_protected_endpoints_open_when_secret_not_configured(client):
    """With RAPIDAPI_PROXY_SECRET unset (local/dev), no header is required."""
    resp = client.get("/ads/search")
    assert resp.status_code == 200


def test_health_never_requires_proxy_secret(client_with_proxy_secret):
    """`/health` must stay reachable for platform health checks even when
    the proxy secret is enforced everywhere else."""
    test_client, _secret = client_with_proxy_secret
    resp = test_client.get("/health")
    assert resp.status_code == 200


def test_ads_search_blocked_without_header_when_secret_configured(
    client_with_proxy_secret,
):
    test_client, _secret = client_with_proxy_secret
    resp = test_client.get("/ads/search")
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"]["code"] == "FORBIDDEN_DIRECT_ACCESS"


def test_ads_search_blocked_with_wrong_header_when_secret_configured(
    client_with_proxy_secret,
):
    test_client, _secret = client_with_proxy_secret
    resp = test_client.get(
        "/ads/search", headers={"X-RapidAPI-Proxy-Secret": "wrong-value"}
    )
    assert resp.status_code == 403


def test_ads_search_allowed_with_correct_header_when_secret_configured(
    client_with_proxy_secret,
):
    test_client, secret = client_with_proxy_secret
    resp = test_client.get(
        "/ads/search", headers={"X-RapidAPI-Proxy-Secret": secret}
    )
    assert resp.status_code == 200


def test_trends_endpoints_also_protected_when_secret_configured(
    client_with_proxy_secret,
):
    test_client, secret = client_with_proxy_secret
    assert test_client.get("/trends/sounds").status_code == 403
    assert test_client.get("/trends/hashtags").status_code == 403
    assert (
        test_client.get(
            "/trends/sounds", headers={"X-RapidAPI-Proxy-Secret": secret}
        ).status_code
        == 200
    )


def test_proxy_secret_header_hidden_from_openapi_schema(client_with_proxy_secret):
    """The proxy secret is injected by RapidAPI itself, not filled in by
    API consumers, so it must not appear as a documented parameter."""
    test_client, secret = client_with_proxy_secret
    spec = test_client.get(
        "/openapi.json", headers={"X-RapidAPI-Proxy-Secret": secret}
    ).json()
    search_params = [
        p["name"] for p in spec["paths"]["/ads/search"]["get"].get("parameters", [])
    ]
    assert "x-rapidapi-proxy-secret" not in [p.lower() for p in search_params]
