"""
매칭 진단 스크립트
==================
eBay CGC10 일본 카드 20개를 PriceCharting DB와 매칭한 결과를 텔레그램으로 전송합니다.
실행: py test_matching.py
"""
from ebay_client import get_token, search_cgc10_japanese
from db import find_psa10_price, _extract_components  # type: ignore
from notifier import send


def run():
    print("eBay 검색 중...")
    token = get_token()
    items = search_cgc10_japanese(token, limit=20)
    print(f"{len(items)}개 검색됨\n")

    matched   = []
    unmatched = []

    for item in items:
        comps = _extract_components(item["title"])
        psa10, matched_name, pc_url = find_psa10_price(item["title"])

        row = {
            "title":        item["title"],
            "price":        item["price"],
            "url":          item["url"],
            "keywords":     comps["keywords"],
            "card_type":    comps["card_type"],
            "card_num":     comps["card_num"],
            "psa10":        psa10,
            "matched_name": matched_name,
            "pc_url":       pc_url,
        }

        if psa10:
            matched.append(row)
        else:
            unmatched.append(row)

        status = f"OK ${psa10:.0f} -> {(matched_name or '')[:40]}" if psa10 else "MISS"
        print(f"[{status}]")
        title_safe = item['title'][:60].encode("cp949", errors="replace").decode("cp949")
        print(f"  eBay: {title_safe}")
        print(f"  kw={comps['keywords'][:2]} type={comps['card_type']} num={comps['card_num']}")
        print()

    # 텔레그램 전송
    lines = [
        f"🔍 <b>매칭 진단 결과</b>",
        f"✅ 매칭 {len(matched)}건 / ❌ 미매칭 {len(unmatched)}건\n",
    ]

    lines.append("─" * 28)
    lines.append("<b>✅ 매칭 성공</b>")
    for r in matched:
        type_tag = f" {r['card_type']}" if r['card_type'] else ""
        num_tag  = f" #{r['card_num']}" if r['card_num'] else ""
        kw       = r['keywords'][0] if r['keywords'] else "?"
        lines.append(
            f"• <a href=\"{r['url']}\">{r['title'][:45]}</a>\n"
            f"  추출: <code>{kw}{type_tag}{num_tag}</code>\n"
            f"  → {(r['matched_name'] or '')[:40]}  PSA10: <b>${r['psa10']:.0f}</b>"
        )

    if unmatched:
        lines.append("")
        lines.append("─" * 28)
        lines.append("<b>❌ 매칭 실패 (추정가 사용됨)</b>")
        for r in unmatched:
            type_tag = f" {r['card_type']}" if r['card_type'] else ""
            num_tag  = f" #{r['card_num']}" if r['card_num'] else ""
            kw       = r['keywords'][0] if r['keywords'] else "?"
            lines.append(
                f"• <a href=\"{r['url']}\">{r['title'][:45]}</a>\n"
                f"  추출: <code>{kw}{type_tag}{num_tag}</code>"
            )

    msg = "\n".join(lines)
    send(msg)
    print(f"\n텔레그램 전송 완료 (매칭률: {len(matched)}/{len(items)})")


if __name__ == "__main__":
    run()
