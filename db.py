"""
Supabase REST API client (raw HTTP — no supabase-py dependency).
Handles price data cache and arbitrage log.
Tables must be created first via schema.sql.
"""
from __future__ import annotations

import re
import requests
from config import SUPABASE_URL, SUPABASE_KEY

_BASE    = f"{SUPABASE_URL}/rest/v1"
_HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=minimal",
}


def _post(path: str, json: dict | list, extra_prefer: str = "") -> requests.Response:
    headers = dict(_HEADERS)
    if extra_prefer:
        headers["Prefer"] = f"{headers['Prefer']},{extra_prefer}"
    return requests.post(f"{_BASE}/{path}", json=json, headers=headers, timeout=30)


def _get(path: str, params: dict) -> requests.Response:
    return requests.get(f"{_BASE}/{path}", params=params, headers=_HEADERS, timeout=15)


# ── Price data ────────────────────────────────────────────────────────────────

def upsert_prices(rows: list[dict]) -> int:
    """Bulk upsert price rows. Returns upserted count."""
    if not rows:
        return 0

    BATCH = 500
    total = 0
    n_batches = (len(rows) + BATCH - 1) // BATCH
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        resp = _post(
            "pokemon_prices",
            batch,
            extra_prefer="resolution=merge-duplicates",
        )
        batch_num = i // BATCH + 1
        if resp.status_code in (200, 201, 204):
            total += len(batch)
            print(f"[DB] 업로드 중... {batch_num}/{n_batches} ({total}/{len(rows)}건)", end="\r")
        else:
            print(f"\n[DB] upsert error {resp.status_code}: {resp.text[:200]}")
    print(f"\n[DB] Supabase 업로드 완료: {total}건")
    return total


def find_psa10_price(ebay_title: str) -> tuple[float | None, str | None, str | None]:
    """
    Match eBay title to PriceCharting PSA10 price.
    Only matches cards released 2010 or later (pre-2010 = ancient, skip).
    Strategy:
      1) name + card_type (e.g. "Charizard VSTAR") → Japanese preferred
      2) name only → Japanese preferred
      3) name only → any region
    Returns (price_usd, matched_name, pc_url) or (None, None, None).
    """
    comps = _extract_components(ebay_title)
    keywords  = comps["keywords"]
    card_type = comps["card_type"]

    if not keywords:
        return None, None, None

    def _search(query: str, jp_only: bool) -> list[dict]:
        params = {
            "select":       "product_id,product_name,console_name,psa_10_price,release_date",
            "product_name": f"ilike.*{query}*",
            "psa_10_price": "gt.0",
            "order":        "psa_10_price.desc",
            "limit":        "20",
        }
        if jp_only:
            params["console_name"] = "ilike.*japan*"
        resp = _get("pokemon_prices", params)
        if resp.status_code != 200:
            return []
        rows = resp.json() or []
        # 2010년 이후만 (release_date 컬럼이 없거나 NULL이면 통과)
        return [
            r for r in rows
            if not r.get("release_date") or r["release_date"] >= "2010-01-01"
        ]

    def _pick(rows: list[dict]) -> tuple[float, str, str] | None:
        if not rows:
            return None
        r = rows[0]
        url = _pc_url(r.get("console_name", ""), r.get("product_name", ""))
        return float(r["psa_10_price"]), r["product_name"], url

    for kw in keywords:
        # Stage 1: name + type (most specific) e.g. "Charizard VSTAR"
        if card_type:
            result = _pick(_search(f"{kw} {card_type}", jp_only=True)) or \
                     _pick(_search(f"{kw} {card_type}", jp_only=False))
            if result:
                return result

        # Stage 2: name only, Japanese
        result = _pick(_search(kw, jp_only=True))
        if result:
            return result

    # Stage 3: first keyword, any region
    result = _pick(_search(keywords[0], jp_only=False))
    if result:
        return result

    return None, None, None


# ── Arbitrage log ─────────────────────────────────────────────────────────────

def log_opportunity(opp: dict):
    """Persist a found opportunity for historical tracking (non-fatal)."""
    item     = opp["item"]
    analysis = opp["analysis"]
    rec      = analysis.get("recommended") or {}

    row = {
        "ebay_item_id":     item.get("item_id", ""),
        "ebay_title":       item["title"][:200],
        "ebay_price_usd":   item["price"],
        "listing_type":     item["listing_type"],
        "psa_10_price_usd": analysis["psa10_price"],
        "best_tier":        rec.get("name", ""),
        "best_roi":         rec.get("roi", 0),
        "is_estimated":     opp.get("is_estimated", False),
        "ebay_url":         item.get("url", ""),
    }
    try:
        _post("arbitrage_log", row)
    except Exception:
        pass


# ── Helpers ───────────────────────────────────────────────────────────────────

_GRADING = re.compile(
    r"\b(cgc|psa|bgs|sgc|10|9\.5|9|8|gem|mint|pristine|graded|grade"
    r"|pokemon|japanese|japan|holographic|cards|lot|pack|fresh"
    r"|sv\w+|sm\w+|xy\w+|bw\w+|dp\w+|rs\w+)\b",
    re.IGNORECASE,
)
# Card type suffixes — keep these for matching
_CARD_TYPE = re.compile(r'\b(VSTAR|VMAX|GX|EX)\b', re.IGNORECASE)
# Card number: "014/172", "4/102" → capture the leading number
_CARD_NUM  = re.compile(r'\b(\d{1,3})/\d{2,4}\b')
_YEAR      = re.compile(r'\b(19|20)\d{2}\b')

# Generic words that are never a card name
_GENERIC = {"holo", "rare", "ultra", "secret", "trainer", "promo", "stamp",
            "set", "card", "select", "shipping", "free", "one", "new", "the"}


def _extract_components(title: str) -> dict:
    """
    Returns dict with:
      keywords  — Pokemon name candidates (longest first)
      card_type — VSTAR / VMAX / GX / EX or None
      card_num  — leading number from "014/172" or None
    """
    # 1. Card type
    tm = _CARD_TYPE.search(title)
    card_type = tm.group(1).upper() if tm else None

    # 2. Card number
    nm = _CARD_NUM.search(title)
    card_num = nm.group(1).lstrip("0") or nm.group(1) if nm else None

    # 3. Clean: remove grading terms, years, card number, card type, lone numbers
    text = _YEAR.sub("", title)
    if nm:
        text = text.replace(nm.group(0), " ")
    if tm:
        text = re.sub(rf'\b{re.escape(tm.group(1))}\b', " ", text, flags=re.IGNORECASE)
    text = _GRADING.sub("", text)
    text = re.sub(r'\b\d+\b', "", text)
    text = re.sub(r'[-/]', " ", text)
    text = re.sub(r'\s+', " ", text).strip()

    # 4. Keywords: non-generic words, longest first
    words = [w for w in text.split() if len(w) > 2 and w.lower() not in _GENERIC]
    words.sort(key=len, reverse=True)

    return {"keywords": words[:4], "card_type": card_type, "card_num": card_num}


def _pc_url(console_name: str, product_name: str) -> str:
    """Construct PriceCharting product page URL."""
    def slug(s: str) -> str:
        s = s.lower()
        s = re.sub(r"[#\[\]'\"().,!?/]", "", s)
        s = re.sub(r"[^a-z0-9]+", "-", s)
        return s.strip("-")
    return f"https://www.pricecharting.com/game/{slug(console_name)}/{slug(product_name)}"


def _is_japanese(console_name: str) -> bool:
    return bool(re.search(r"japan", console_name, re.IGNORECASE))
