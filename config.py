import os
from dotenv import load_dotenv

load_dotenv()

EBAY_APP_ID  = os.getenv("EBAY_APP_ID", "")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID", "")

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

PRICECHARTING_TOKEN  = os.getenv("PRICECHARTING_TOKEN", "")
ANTHROPIC_API_KEY    = os.getenv("ANTHROPIC_API_KEY", "")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

EXCHANGE_RATE_KRW = float(os.getenv("EXCHANGE_RATE_KRW", "1380"))
MIN_ROI           = float(os.getenv("MIN_ROI", "50"))
MIN_PRICE_USD     = float(os.getenv("MIN_PRICE_USD", "100"))  # 100불 미만은 ROI 불가

SCHEDULE_TIME = "07:00"

# 진스카 PSA 대행 등급비 (스마트스토어 기준, KRW)
GRADING_TIERS = [
    {"name": "벨류 플러스", "krw": 101_000, "turnaround": "2~3개월"},
    {"name": "벨류 맥스",   "krw": 132_000, "turnaround": "~2개월"},
    {"name": "레귤러",      "krw": 160_600, "turnaround": "~1개월"},
]
