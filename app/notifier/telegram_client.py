from __future__ import annotations

import os

from app.config import Config

from .http import post_json


def send_text(chat_id: str, text: str, *, html: bool = False) -> bool:
    if not Config.TG_BOT_TOKEN:
        return False

    payload = {
        "chat_id": chat_id,
        "text": text if html else _to_safe_html(text),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        response = post_json(_bot_url("sendMessage"), payload=payload)
        return response.status_code == 200
    except Exception:
        return False


def send_document(chat_id: str, file_path: str, *, caption: str | None = None) -> bool:
    if not Config.TG_BOT_TOKEN:
        return False

    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption

    try:
        with open(file_path, "rb") as file_handle:
            import requests

            response = requests.post(
                _bot_url("sendDocument"),
                data=data,
                files={"document": (os.path.basename(file_path), file_handle)},
                timeout=60,
            )
        return response.status_code == 200
    except Exception:
        return False


def send_photo(chat_id: str, file_path: str, *, caption: str | None = None) -> bool:
    if not Config.TG_BOT_TOKEN:
        return False

    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption

    try:
        with open(file_path, "rb") as file_handle:
            import requests

            response = requests.post(
                _bot_url("sendPhoto"),
                data=data,
                files={"photo": (os.path.basename(file_path), file_handle)},
                timeout=60,
            )
        return response.status_code == 200
    except Exception:
        return False


def delete_message(chat_id: str, message_id: str) -> None:
    if not Config.TG_BOT_TOKEN or not message_id:
        return

    try:
        post_json(
            _bot_url("deleteMessage"),
            payload={"chat_id": chat_id, "message_id": int(message_id)},
            timeout=10,
        )
    except Exception:
        return


def _bot_url(method: str) -> str:
    return f"https://api.telegram.org/bot{Config.TG_BOT_TOKEN}/{method}"


def _to_safe_html(text: str) -> str:
    safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return safe_text.replace("📔", "<b>📔").replace("\n📺", "</b>\n📺")
