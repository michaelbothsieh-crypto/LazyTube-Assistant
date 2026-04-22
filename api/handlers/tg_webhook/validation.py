from __future__ import annotations

from app.config import Config


def normalize_command_text(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("/") and "@" in text:
        return f"{text.split()[0].split('@')[0]}{' ' + ' '.join(text.split()[1:]) if len(text.split()) > 1 else ''}".strip()
    return text


def validate_url(url: str) -> str | None:
    if not url.startswith(("http://", "https://")):
        return f"無效的 URL：<code>{url[:100]}</code>"
    if len(url) > Config.MAX_URL_LENGTH:
        return f"URL 長度超過限制（{Config.MAX_URL_LENGTH}）。"
    return None


def is_allowed_user(user_id: str, chat_id: str) -> bool:
    allowed = Config.get_allowed_users()
    if not allowed:
        return True
    return user_id in allowed or chat_id in allowed
