"""
Card Arbitrage Bot
==================
매일 07:00에 eBay에서 CGC 10 일본판 포켓몬 카드를 검색하고
진스카 등급 대행 비용을 포함한 PSA 10 차익거래 기회를 텔레그램으로 전송합니다.

실행:
  py main.py           → 07:00 자동 스케줄 (상시 실행)
  py main.py --now     → 즉시 실행 (테스트용)
  py main.py --sync    → PriceCharting DB만 업데이트 후 종료
"""
import re
import sys
import time
import schedule
from datetime import datetime

_YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')

from config import SCHEDULE_TIME
from ebay_client import get_token, search_cgc10_japanese
from pricecharting_client import download_and_parse
from db import upsert_prices, find_psa10_price, log_opportunity
from arbitrage import analyze
from notifier import send, send_report
from vision import verify_match


def sync_pricecharting():
    """Download PriceCharting CSV and upsert to Supabase."""
    print(f"[{_now()}] PriceCharting 데이터 동기화 시작...")
    rows = download_and_parse()
    if rows:
        count = upsert_prices(rows)
        print(f"[{_now()}] Supabase upsert 완료: {count}건")
    else:
        print(f"[{_now()}] PriceCharting 데이터 없음 — 기존 DB 유지")


def run_scan(sync: bool = True):
    print(f"[{_now()}] ===== 스캔 시작 =====")

    # 1. PriceCharting DB 갱신 (주 1회 별도 실행 권장)
    if sync:
        sync_pricecharting()

    # 2. eBay 검색
    try:
        token = get_token()
        items = search_cgc10_japanese(token)
    except Exception as e:
        msg = f"❌ eBay API 오류: {e}"
        print(msg)
        send(msg)
        return

    print(f"[{_now()}] eBay: {len(items)}개 검색됨")

    # 3. 각 카드 ROI 분석
    opportunities = []

    for item in items:
        # 제목에서 연도 감지 → 2010년 이전 카드 스킵
        ym = _YEAR_RE.search(item["title"])
        if ym and int(ym.group(0)) < 2010:
            continue

        psa10_price, matched_name, pc_url, console_name = find_psa10_price(item["title"])

        if psa10_price is None:
            continue

        # 비율 체크: PSA10이 CGC10의 8배 초과면 오매칭으로 간주
        if psa10_price > item["price"] * 8:
            continue

        # Vision 검증: eBay 이미지가 매칭 카드와 일치하는지 확인
        ok = verify_match(item.get("image", ""), matched_name or "", console_name or "")
        print(f"[Vision] {'✓' if ok else '✗'} {(matched_name or '')[:40]}")
        if not ok:
            print(f"[Vision] 오매칭 제거: {item['title'][:60]}")
            continue

        result = analyze(item["price"], psa10_price)

        if result["any_feasible"]:
            opp = {
                "item":         item,
                "analysis":     result,
                "is_estimated": False,
                "matched_name": matched_name,
                "pc_url":       pc_url,
            }
            opportunities.append(opp)
            log_opportunity(opp)

    # 4. ROI 내림차순 정렬 후 상위 30개만
    opportunities.sort(
        key=lambda x: x["analysis"]["recommended"]["roi"],
        reverse=True,
    )
    opportunities = opportunities[:30]

    print(f"[{_now()}] 기회 발견: {len(opportunities)}건 (상위 30개)")

    # 5. 텔레그램 전송
    send_report(opportunities)
    print(f"[{_now()}] 리포트 전송 완료")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--sync" in args:
        sync_pricecharting()
        sys.exit(0)

    if "--scan-only" in args:
        run_scan(sync=False)
        sys.exit(0)

    if "--now" in args:
        run_scan(sync=True)
        sys.exit(0)

    print(f"카드 아비트리지 봇 시작 — 매일 {SCHEDULE_TIME} 자동 실행")
    print("즉시 실행:   py main.py --now")
    print("DB만 갱신:   py main.py --sync")

    schedule.every().day.at(SCHEDULE_TIME).do(run_scan)

    while True:
        schedule.run_pending()
        time.sleep(30)
