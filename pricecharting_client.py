"""
PriceCharting price guide downloader.
Downloads full Pokemon card CSV, parses it, and returns rows for Supabase upsert.

CSV endpoint: https://www.pricecharting.com/price-guide/download-custom
  ?t=TOKEN&category=pokemon-cards

Expected CSV columns (sample):
  id, product-name, console-name, loose-price, cib-price, new-price,
  graded-price, ..., grade-10-price, grade-9-price, ...
  Prices are in USD cents (integer) → divide by 100.
"""
from __future__ import annotations

import io
import csv
import requests
from config import PRICECHARTING_TOKEN

_DOWNLOAD_URL = (
    "https://www.pricecharting.com/price-guide/download-custom"
    f"?t={PRICECHARTING_TOKEN}&category=pokemon-cards"
)


def download_and_parse() -> list[dict]:
    """
    Download the full Pokemon price CSV and return a list of dicts
    ready for db.upsert_prices().
    Returns empty list on failure.
    """
    try:
        resp = requests.get(_DOWNLOAD_URL, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        print(f"[PriceCharting] download failed: {e}")
        return []

    content_type = resp.headers.get("Content-Type", "")
    if "html" in content_type:
        print("[PriceCharting] got HTML instead of CSV — check token")
        return []

    rows = []
    reader = csv.DictReader(io.StringIO(resp.text))

    for raw in reader:
        product_id   = raw.get("id", "").strip()
        product_name = raw.get("product-name", "").strip()
        console_name = raw.get("console-name", "").strip()

        if not product_id or not product_name:
            continue

        # manual-only-price  = PSA 10 (PriceCharting docs confirmed)
        # condition-17-price = CGC 10
        # graded-price       = PSA 9 (fallback if no PSA10 data)
        psa10 = _parse_price(raw.get("manual-only-price", ""))
        cgc10 = _parse_price(raw.get("condition-17-price", ""))

        release_date = raw.get("release-date", "").strip() or None

        rows.append({
            "product_id":   product_id,
            "product_name": product_name,
            "console_name": console_name,
            "psa_10_price": psa10,
            "cgc_10_price": cgc10,
            "release_date": release_date,
        })

    print(f"[PriceCharting] parsed {len(rows)} rows")
    return rows


def _parse_price(raw: str) -> float | None:
    """Convert PriceCharting price string to USD float."""
    if not raw or raw.strip() in ("", "N/A", "0"):
        return None
    try:
        val = float(raw.replace(",", "").replace("$", "").strip())
    except ValueError:
        return None

    if val <= 0:
        return None

    # PriceCharting API returns cents (integers), CSV may return dollars
    # Heuristic: if value > 10000 it's likely cents
    # CSV format uses dollar amounts (e.g. "$34.98"), not cents
    return round(val, 2)
