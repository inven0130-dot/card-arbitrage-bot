"""
Claude Haiku vision으로 eBay 카드 이미지가 PriceCharting 매칭과 일치하는지 검증.
"""
from __future__ import annotations
import anthropic
from config import ANTHROPIC_API_KEY

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def verify_match(image_url: str, matched_name: str, console_name: str) -> bool:
    """
    eBay 카드 이미지가 PriceCharting 매칭 결과와 같은 카드인지 확인.
    image_url이 없거나 API 키 없으면 True(통과) 반환.
    """
    if not image_url or not ANTHROPIC_API_KEY:
        return True

    try:
        resp = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "url", "url": image_url},
                    },
                    {
                        "type": "text",
                        "text": (
                            f"This is a CGC-graded Pokemon card listed on eBay. "
                            f"I matched it to: '{matched_name}' from '{console_name}'. "
                            f"Does the card visible inside the case match this? "
                            f"Answer only YES or NO."
                        ),
                    },
                ],
            }],
        )
        answer = resp.content[0].text.strip().upper()
        return answer.startswith("YES")
    except Exception as e:
        print(f"[Vision] 검증 실패 (통과 처리): {e}")
        return True
