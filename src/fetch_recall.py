"""Fetch the recall record, preferring a live openFDA confirmation but always
falling back to the committed seed file so the app renders offline.

The seed file is the trusted source for every fact the match engine relies on
(lot codes, states, dates). A successful live call only attaches extra,
display-only confirmation fields -- it never overwrites those trusted facts,
since openFDA's schema and the seed record's schema are not guaranteed to
line up field-for-field.
"""

import json
from pathlib import Path

import requests

OPENFDA_URL = "https://api.fda.gov/food/enforcement.json"
OPENFDA_QUERY = 'recalling_firm:"Midwest Poultry"'
SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_recall_record.json"
TIMEOUT_SECONDS = 5


def load_seed_record(path: Path = SEED_PATH) -> dict:
    with open(path) as f:
        return json.load(f)


def fetch_recall_record(prefer_live: bool = True) -> tuple[dict, str]:
    """Return (record, source) where source is "live_openfda" or "seed_fallback".

    Any failure at all -- network error, timeout, bad JSON, empty results,
    unexpected schema -- silently falls back to the seed record. Availability
    matters more than granular error handling for a demo like this.
    """
    seed = load_seed_record()
    if not prefer_live:
        return seed, "seed_fallback"

    try:
        resp = requests.get(
            OPENFDA_URL,
            params={"search": OPENFDA_QUERY, "limit": 5},
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return seed, "seed_fallback"

        live_extra = {
            "live_status": results[0].get("status"),
            "live_distribution_pattern": results[0].get("distribution_pattern"),
        }
        enriched = {**seed, "live_confirmation": live_extra}
        return enriched, "live_openfda"
    except Exception:
        return seed, "seed_fallback"
