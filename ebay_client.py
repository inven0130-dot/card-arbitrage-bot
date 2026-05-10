import base64
import requests
from config import EBAY_APP_ID, EBAY_CERT_ID, MIN_PRICE_USD

_TOKEN_CACHE: dict = {}


def get_token() -> str:
    import time
    if _TOKEN_CACHE.get("expires_at", 0) > time.time() + 60:
        return _TOKEN_CACHE["token"]

    creds = base64.b64encode(f"{EBAY_APP_ID}:{EBAY_CERT_ID}".encode()).decode()
    resp = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data="grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope",
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    import time as t
    _TOKEN_CACHE["token"] = data["access_token"]
    _TOKEN_CACHE["expires_at"] = t.time() + data.get("expires_in", 7200)
    return _TOKEN_CACHE["token"]


def search_cgc10_japanese(token: str, limit: int = 100) -> list[dict]:
    """
    Search eBay for CGC 10 Japanese Pokemon cards.
    Min price $100, excludes Pristine.
    Returns list of dicts with title, price, url, listing_type, item_id, end_date.
    """
    resp = requests.get(
        "https://api.ebay.com/buy/browse/v1/item_summary/search",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "q": 'pokemon japanese CGC 10 -pristine -"pristine 10" -"CGC Pristine" -sealdass -sticker -seal -file -binder -lot -pack -album',
            "category_ids": "183454",  # Pokemon TCG
            "filter": f"price:[{int(MIN_PRICE_USD)}..],priceCurrency:USD",
            "fieldgroups": "EXTENDED",
            "sort": "price",
            "limit": limit,
        },
        timeout=15,
    )
    resp.raise_for_status()

    items = []
    for raw in resp.json().get("itemSummaries", []):
        title = raw.get("title", "")
        if "pristine" in title.lower():
            continue

        price = float(raw.get("price", {}).get("value", 0))
        if price < MIN_PRICE_USD:
            continue

        buying_opts = raw.get("buyingOptions", [])
        is_auction = "AUCTION" in buying_opts

        items.append({
            "title":        title,
            "price":        price,
            "url":          raw.get("itemWebUrl", ""),
            "listing_type": "auction" if is_auction else "buy_now",
            "item_id":      raw.get("itemId", ""),
            "end_date":     raw.get("itemEndDate", ""),
            "image":        raw.get("image", {}).get("imageUrl", ""),
        })

    return items
