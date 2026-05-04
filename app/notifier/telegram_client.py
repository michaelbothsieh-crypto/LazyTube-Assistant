from __future__ import annotations

import os

from .http import post_json


class TelegramClient:
    def __init__(self, bot_token: str) -> None:
        self._token = bot_token

    def send_text(self, chat_id: str, text: str, *, html: bool = False) -> bool:
        payload = {
            "chat_id": chat_id,
            "text": text if html else _to_safe_html(text),
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "link_preview_options": {"is_disabled": True},
        }
        try:
            response = post_json(self._bot_url("sendMessage"), payload=payload)
            return response.status_code == 200
        except Exception:
            return False

    def send_document(self, chat_id: str, file_path: str, *, caption: str | None = None) -> bool:
        return self._send_file("sendDocument", "document", chat_id, file_path, caption=caption)

    def send_photo(self, chat_id: str, file_path: str, *, caption: str | None = None) -> bool:
        return self._send_file("sendPhoto", "photo", chat_id, file_path, caption=caption)

    def send_photo_url(self, chat_id: str, image_url: str, *, caption: str | None = None) -> bool:
        payload = {"chat_id": chat_id, "photo": image_url}
        if caption:
            payload["caption"] = caption
        try:
            response = post_json(self._bot_url("sendPhoto"), payload=payload, timeout=30)
            return response.status_code == 200
        except Exception:
            return False

    def _send_file(
        self,
        method: str,
        field_name: str,
        chat_id: str,
        file_path: str,
        *,
        caption: str | None = None,
    ) -> bool:
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        try:
            with open(file_path, "rb") as file_handle:
                import requests

                response = requests.post(
                    self._bot_url(method),
                    data=data,
                    files={field_name: (os.path.basename(file_path), file_handle)},
                    timeout=60,
                )
            return response.status_code == 200
        except Exception:
            return False

    def delete_message(self, chat_id: str, message_id: str) -> None:
        if not message_id:
            return
        try:
            post_json(
                self._bot_url("deleteMessage"),
                payload={"chat_id": chat_id, "message_id": int(message_id)},
                timeout=10,
            )
        except Exception:
            return

    def _bot_url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self._token}/{method}"


def _to_safe_html(text: str) -> str:
    safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return safe_text.replace("📔", "<b>📔").replace("\n📺", "</b>\n📺")


def html_escape(text: str) -> str:
    """對純文字欄位做最小 HTML 轉義，確保不破壞 Telegram HTML parse_mode。"""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
