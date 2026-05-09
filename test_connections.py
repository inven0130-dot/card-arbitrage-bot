"""Quick connectivity test for all APIs."""
import sys

def test_ebay():
    from ebay_client import get_token, search_cgc10_japanese
    token = get_token()
    print(f"[eBay] 토큰 취득 성공")
    items = search_cgc10_japanese(token, limit=5)
    print(f"[eBay] 검색 결과: {len(items)}개")
    for it in items[:3]:
        print(f"  [{it['listing_type']}] ${it['price']:.0f} — {it['title'][:60]}")
    return items


def test_pricecharting():
    from pricecharting_client import download_and_parse
    rows = download_and_parse()
    print(f"[PriceCharting] 파싱 결과: {len(rows)}행")
    if rows:
        jp = [r for r in rows if r.get("psa_10_price") and "japan" in (r.get("console_name") or "").lower()]
        print(f"  Japanese cards with PSA10 price: {len(jp)}")
        for r in jp[:5]:
            price = r['psa_10_price']
            name  = r['product_name']
            con   = r['console_name']
            print(f"  PSA10=${price} | {name} | {con}")
    return rows


def test_supabase():
    import requests
    from config import SUPABASE_URL, SUPABASE_KEY
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/pokemon_prices?select=count&limit=1",
        headers=headers, timeout=10
    )
    if resp.status_code == 404 and "schema cache" in resp.text:
        print("[Supabase] 연결 OK — 테이블 미생성 (schema.sql 실행 필요)")
    elif resp.status_code == 200:
        print(f"[Supabase] OK — 현재 행 수: {resp.json()}")
    else:
        print(f"[Supabase] 오류 {resp.status_code}: {resp.text[:200]}")


if __name__ == "__main__":
    tests = sys.argv[1:] or ["ebay", "pricecharting", "supabase"]

    if "ebay" in tests:
        try:
            test_ebay()
        except Exception as e:
            print(f"[eBay] 오류: {e}")

    if "pricecharting" in tests:
        try:
            test_pricecharting()
        except Exception as e:
            print(f"[PriceCharting] 오류: {e}")

    if "supabase" in tests:
        try:
            test_supabase()
        except Exception as e:
            print(f"[Supabase] 오류: {e}")
