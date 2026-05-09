"""
PriceCharting 일별 CSV 저장 스크립트
=====================================
실행: py download_daily.py

매일 한 번 실행하면 price_data/ 폴더에 날짜별 CSV가 쌓입니다.
Windows 작업 스케줄러로 자동화 권장 (Railway와 별개로 로컬에서 실행).

저장 경로: price_data/YYYY-MM-DD.csv
용량: 하루 약 5~8MB (CSV 압축 저장)
"""
import os
import gzip
import shutil
import requests
from datetime import date
from config import PRICECHARTING_TOKEN

SAVE_DIR  = os.path.join(os.path.dirname(__file__), "price_data")
TODAY     = date.today().isoformat()          # e.g. 2026-05-09
SAVE_PATH = os.path.join(SAVE_DIR, f"{TODAY}.csv.gz")
URL       = (
    f"https://www.pricecharting.com/price-guide/download-custom"
    f"?t={PRICECHARTING_TOKEN}&category=pokemon-cards"
)


def download():
    os.makedirs(SAVE_DIR, exist_ok=True)

    if os.path.exists(SAVE_PATH):
        print(f"[{TODAY}] 이미 저장됨: {SAVE_PATH}")
        return

    print(f"[{TODAY}] 다운로드 중...")
    resp = requests.get(URL, timeout=60, stream=True)
    resp.raise_for_status()

    # gzip 압축 저장 (CSV ~18MB → gz ~3MB)
    with gzip.open(SAVE_PATH, "wb") as f:
        shutil.copyfileobj(resp.raw, f)

    size_mb = os.path.getsize(SAVE_PATH) / 1024 / 1024
    print(f"[{TODAY}] 저장 완료: {SAVE_PATH} ({size_mb:.1f} MB)")


def list_saved():
    if not os.path.exists(SAVE_DIR):
        print("저장된 파일 없음")
        return
    files = sorted(os.listdir(SAVE_DIR))
    total = sum(os.path.getsize(os.path.join(SAVE_DIR, f)) for f in files)
    print(f"저장된 파일: {len(files)}개 / 총 {total/1024/1024:.1f} MB")
    for f in files[-10:]:  # 최근 10개만 표시
        path = os.path.join(SAVE_DIR, f)
        mb = os.path.getsize(path) / 1024 / 1024
        print(f"  {f}  ({mb:.1f} MB)")


if __name__ == "__main__":
    import sys
    if "--list" in sys.argv:
        list_saved()
    else:
        download()
        list_saved()
