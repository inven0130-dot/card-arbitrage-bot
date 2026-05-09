"""
처음 한 번만 실행. 텔레그램 봇에 /start 보내고 이 스크립트 실행하면
chat_id 자동으로 .env에 저장됨.
"""
import os
import requests
from dotenv import load_dotenv, set_key

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
resp = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates")
data = resp.json()

updates = data.get("result", [])
if not updates:
    print("❌ 메시지를 찾을 수 없습니다.")
    print("→ 텔레그램에서 @card0130_bot 에게 /start 를 먼저 보내고 다시 실행하세요.")
else:
    chat_id = str(updates[-1]["message"]["chat"]["id"])
    set_key(".env", "TELEGRAM_CHAT_ID", chat_id)
    print(f"✅ Chat ID 저장 완료: {chat_id}")
