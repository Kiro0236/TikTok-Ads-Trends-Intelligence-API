"""
Tolerant normalization for optional string query parameters.

Some API clients/consoles (including some third-party API marketplace
testing UIs) occasionally send a text field JSON-encoded rather than
as a plain string — e.g. sending `"US"` (with literal quotes) or
`["US"]` (wrapped in an array) when the user typed `US` into a form
field configured with the wrong parameter type upstream.

Query strings are always plain text at the HTTP level, so this isn't
something FastAPI/Pydantic can "fix" — by the time it reaches us, the
literal characters `"US"` or `["US"]` are just a string that happens
to be the wrong length. Rather than hard-failing with a 422 for a
client-side formatting quirk we don't control, we normalize common
wrapping patterns before validation, and fall back to `None` for
anything empty or unparseable rather than raising.
"""
import json


def normalize_optional_str(value: str | None) -> str | None:
    """Clean up an optional string query param.

    - `None` / empty / whitespace-only -> `None`
    - `'"US"'` (JSON-quoted string) -> `'US'`
    - `'["US"]'` (single-element JSON array of strings) -> `'US'`
    - anything else -> stripped as-is
    """
    if value is None:
        return None

    cleaned = value.strip()
    if not cleaned:
        return None

    # Unwrap a JSON-quoted string: "US" -> US
    if len(cleaned) >= 2 and cleaned[0] == '"' and cleaned[-1] == '"':
        cleaned = cleaned[1:-1].strip()
        return cleaned or None

    # Unwrap a single-element JSON array of strings: ["US"] -> US
    if cleaned.startswith("[") and cleaned.endswith("]"):
        try:
            parsed = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], str):
            unwrapped = parsed[0].strip()
            return unwrapped or None
        # Malformed/unexpected array shape: don't guess further, don't crash.
        return None

    return cleaned
