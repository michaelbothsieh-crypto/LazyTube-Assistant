from __future__ import annotations

from app.config import Config

from .http import post_json

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def send_text(chat_id: str, text: str) -> bool:
    return push_messages(chat_id, [{"type": "text", "text": text}])


def push_messages(chat_id: str, messages: list[dict]) -> bool:
    if not Config.LINE_CHANNEL_ACCESS_TOKEN:
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Config.LINE_CHANNEL_ACCESS_TOKEN}",
    }
    try:
        response = post_json(
            LINE_PUSH_URL,
            payload={"to": chat_id, "messages": messages},
            headers=headers,
            timeout=30,
        )
        return response.status_code == 200
    except Exception:
        return False
