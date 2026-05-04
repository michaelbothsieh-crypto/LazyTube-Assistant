from __future__ import annotations

from .http import post_json

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


class LineClient:
    def __init__(self, access_token: str) -> None:
        self._token = access_token

    def send_text(self, chat_id: str, text: str) -> bool:
        return self.push_messages(chat_id, [{"type": "text", "text": text}])

    def send_image_url(self, chat_id: str, image_url: str, *, caption: str | None = None) -> bool:
        messages = [
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url,
            }
        ]
        if caption:
            messages.append({"type": "text", "text": caption[:5000]})
        return self.push_messages(chat_id, messages)

    def push_messages(self, chat_id: str, messages: list[dict]) -> bool:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
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
