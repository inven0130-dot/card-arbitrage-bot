from __future__ import annotations
import requests
from datetime import datetime
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, MIN_ROI

_BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send(text: str):
    for i in range(0, max(len(text), 1), 4096):
        requests.post(
            f"{_BASE}/sendMessage",
            json={
                "chat_id":                  TELEGRAM_CHAT_ID,
                "text":                     text[i:i+4096],
                "parse_mode":               "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )


def send_report(opportunities: list[dict]):
    send(_format(opportunities))


def _format(opps: list[dict]) -> str:
    now = datetime.now().strftime("%m/%d %H:%M")

    if not opps:
        return f"📭 {now} — ROI {int(MIN_ROI)}%+ 매물 없음"

    lines = [
        f"🎯 <b>CGC10→PSA10</b>  |  {now}  |  <b>{len(opps)}건</b>",
        "",
    ]

    for i, opp in enumerate(opps, 1):
        item      = opp["item"]
        analysis  = opp["analysis"]
        rec       = analysis["recommended"]
        pc_url    = opp.get("pc_url")
        estimated = opp.get("is_estimated", False)

        listing = "🔨" if item["listing_type"] == "auction" else "💳"
        est_tag = " <i>*추정가</i>" if estimated else ""

        # 카드 제목 (짧게)
        title = item["title"][:50].rstrip()

        # ROI 라인
        if item["listing_type"] == "auction":
            roi_line = (
                f"최대입찰 <b>${rec['max_buy_usd']:.0f}</b>  │  "
                f"ROI <b>{rec['roi']}%</b>  │  수익 ${rec['profit_usd']:.0f}"
            )
        else:
            roi_line = (
                f"ROI <b>{rec['roi']}%</b>  │  수익 <b>${rec['profit_usd']:.0f}</b>"
            )

        # 링크
        links = f"<a href=\"{item['url']}\">eBay</a>"
        if pc_url:
            links += f"  ·  <a href=\"{pc_url}\">PriceCharting</a>"

        lines += [
            f"<b>{i}.</b> {listing} {title}",
            f"CGC10 <b>${item['price']:.0f}</b>  →  PSA10 <b>${analysis['psa10_price']:.0f}</b>{est_tag}",
            roi_line,
            f"📦 {rec['name']} ({rec['turnaround']})  |  🔗 {links}",
            "",
        ]

    return "\n".join(lines)
