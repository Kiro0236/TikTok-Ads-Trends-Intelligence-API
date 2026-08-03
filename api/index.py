"""
Vercel serverless entrypoint.

Vercel's Python runtime discovers the ASGI `app` object exported from
this module (see vercel.json rewrites -> api/index.py).
"""
from app.main import app  # noqa: F401
