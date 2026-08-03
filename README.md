# TikTok Ads Intelligence API

A FastAPI service that helps e-commerce owners, media buyers, agencies and
video editors discover high-performing TikTok ad creatives and analyze
competitor campaigns — returned as clean, normalized JSON.

## Status of this build

This codebase ships in **mock data mode** by default: `app/clients/mock_provider_client.py`
generates deterministic, realistic-looking sample data (ads, sounds,
hashtags) entirely in Python, with no external network calls. This lets you
run and integrate against the full API surface — search, details, trends,
pagination, caching, error handling — immediately.

**Important:** this project does not scrape TikTok or any other platform,
and does not include a video-download feature. Those were deliberately
left out. To go live with real data, implement `DataProviderClient`
(`app/clients/base_client.py`) against a data source you are authorized to
use — for example the official TikTok Business/Marketing API, or a
licensed third-party ads-intelligence data vendor — and wire it in via
`app/core/dependencies.py::get_data_provider`. Nothing else in the
codebase needs to change.

## Architecture

```
tiktok_ads_api/
├── api/index.py              # Vercel ASGI entrypoint
├── app/
│   ├── main.py                # FastAPI app factory
│   ├── routers/                # HTTP layer (ads, trends)
│   ├── services/                # Business logic, cache orchestration
│   ├── clients/                  # DataProviderClient interface + mock impl
│   ├── schemas/                   # Public Pydantic v2 response contracts
│   ├── models/                     # Internal "raw" domain dataclasses
│   ├── cache/                       # Upstash Redis REST client + key builder
│   ├── core/                         # Settings, dependency injection
│   ├── utils/                         # Pagination helpers
│   └── exceptions/                     # Custom errors + handlers
├── requirements.txt
├── vercel.json
└── .env.example
```

## Endpoints

| Method | Path             | Purpose                                   | Cache TTL |
|--------|------------------|--------------------------------------------|-----------|
| GET    | `/ads/search`    | Find top-performing ads                    | 12h       |
| GET    | `/ads/details`   | Full campaign intelligence report          | 12h       |
| GET    | `/trends/sounds` | Trending sounds                            | 24h       |
| GET    | `/trends/hashtags` | Trending hashtags                        | 24h       |
| GET    | `/health`        | Health check                               | —         |

Interactive docs are auto-generated at `/docs` (Swagger UI) and `/redoc`.

## Environment variables

All configuration is read from environment variables (see `app/core/config.py`). Copy `.env.example` to `.env` for local development; on Vercel, set these under **Project → Settings → Environment Variables**.

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_ENV` | No | `development` | `development`, `staging`, or `production`. Informational only. |
| `DEBUG` | No | `false` | Enables verbose logging. |
| `DATA_PROVIDER_MODE` | No | `mock` | `mock` returns realistic sample data with no external calls. `live` switches to `LiveDataProviderClient`, currently a stub — see "Going live with real data" below. |
| `DATA_PROVIDER_API_KEY` | Only in `live` mode | — | API key/token for your authorized data source. |
| `DATA_PROVIDER_BASE_URL` | Only in `live` mode | — | Base URL of your authorized data source. |
| `UPSTASH_REDIS_REST_URL` | No | — | Upstash Redis REST endpoint. If unset, caching is silently disabled and every request is served fresh — the API still works. |
| `UPSTASH_REDIS_REST_TOKEN` | No | — | Upstash Redis REST token, paired with the URL above. |
| `RAPIDAPI_PROXY_SECRET` | Recommended in production | — | Value from your RapidAPI provider dashboard (Security tab). When set, all `/ads/*` and `/trends/*` requests must include a matching `X-RapidAPI-Proxy-Secret` header or receive `403 Forbidden`. Left unset in local dev to skip this check. |
| `RATE_LIMIT_ENABLED` | No | `false` | Reserved for future per-key rate limiting. |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | No | `60` | Reserved for future per-key rate limiting. |

### Setting these up on Vercel

1. Deploy the project once (`vercel deploy` or via the Git integration) so the project exists in your Vercel dashboard.
2. Go to **Project → Settings → Environment Variables**.
3. Add each variable above that applies to your environment (at minimum: `DATA_PROVIDER_MODE`, and once you have a RapidAPI listing, `RAPIDAPI_PROXY_SECRET`). Scope them to **Production** (and **Preview** if you want preview deployments to behave the same way).
4. Redeploy — Vercel does not hot-reload environment variable changes into already-running deployments.

**Important:** `RAPIDAPI_PROXY_SECRET` should only be set in Production once your RapidAPI listing exists; setting it too early will lock you out of testing the raw Vercel URL directly (which is, by design, exactly what it's for once RapidAPI is in front of it).

## Running the test suite

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

The suite (`tests/test_api.py`) runs entirely in-process against the app (no server needed to be running) and covers:

- Every endpoint (`/health`, `/ads/search`, `/ads/details`, `/trends/sounds`, `/trends/hashtags`) returning `200` with a well-formed body in mock mode
- Validation error paths (`422` on an invalid date range, `404` on an unknown `ad_id`)
- `X-RapidAPI-Proxy-Secret` enforcement: requests are blocked with `403` when the secret is configured and missing/wrong, allowed through with the correct header, and `/health` stays reachable either way
- The proxy secret header staying hidden from the generated OpenAPI schema

Run this before every commit/push, and definitely before a Vercel deploy.

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs

## Example requests

```bash
curl "http://127.0.0.1:8000/ads/search?country_code=US&sort_by=ctr&page=1&page_size=10"

curl "http://127.0.0.1:8000/ads/details?ad_id=ad_1234567890"

curl "http://127.0.0.1:8000/trends/sounds?country_code=US"

curl "http://127.0.0.1:8000/trends/hashtags?country_code=US&industry_id=Fashion"
```

## Caching

Uses [Upstash Redis](https://upstash.com) via its REST API (works from
serverless/edge runtimes). If `UPSTASH_REDIS_REST_URL` /
`UPSTASH_REDIS_REST_TOKEN` are not set, caching is silently disabled and
every request is served fresh — the API still works, just without the
latency/cost benefits of caching.

Cache keys are namespaced by endpoint and request parameters, e.g.:

```
ads_search:US:Beauty & Personal Care:skincare:ctr:1:20
```

## Error format

All errors follow one consistent JSON envelope:

```json
{
  "error": {
    "code": "AD_NOT_FOUND",
    "message": "The requested advertisement could not be found.",
    "details": { "ad_id": "ad_123" }
  }
}
```

## Deploying to Vercel

```bash
vercel deploy
```

`vercel.json` points Vercel at `api/index.py` as the single Vercel Function and rewrites every path (`/ads/*`, `/trends/*`, `/health`, `/docs`, `/openapi.json`) to it, since the app's routes live at the root rather than under `/api`. `.python-version` pins the runtime to Python 3.12, matching what's declared here and avoiding drift if Vercel's default version changes. No other configuration is required — Python dependencies are installed automatically from `requirements.txt`.

## Importing into RapidAPI Studio

1. Deploy to Vercel and confirm `https://<your-project>.vercel.app/openapi.json` loads.
2. In RapidAPI Studio, choose **Import → OpenAPI/Swagger** and paste that URL (or upload the downloaded `openapi.json`).
3. RapidAPI will generate one endpoint per path (`/ads/search`, `/ads/details`, `/trends/sounds`, `/trends/hashtags`) with parameters and response schemas pulled directly from the Pydantic models — no manual re-entry needed.
4. Set your Vercel deployment URL as the base URL / origin in the RapidAPI provider dashboard.
5. Once your listing exists, copy the proxy secret from the dashboard's **Security** tab into the `RAPIDAPI_PROXY_SECRET` environment variable on Vercel (see above) and redeploy — RapidAPI injects this header automatically on every proxied request, so nothing changes for your subscribers.

Note: the `X-RapidAPI-Proxy-Secret` header itself is intentionally excluded from the generated OpenAPI schema (`include_in_schema=False`) so it doesn't show up as a fillable parameter for API consumers — RapidAPI's proxy adds it transparently.

## Going live with real data

1. Implement `app/clients/live_provider_client.py`, subclassing
   `DataProviderClient` and calling your authorized data source.
2. Set `DATA_PROVIDER_MODE=live` and the relevant `DATA_PROVIDER_*` env vars.
3. Update `get_data_provider()` in `app/core/dependencies.py` to return
   your new class when `settings.data_provider_mode == "live"`.

No router, service, schema, or cache code needs to change.

## A note on how this was built

The implementation of this project was developed with AI assistance
(Claude, Anthropic). Architecture decisions, data-source vetting, and
security/monetization strategy were directed and validated by the project owner.