from __future__ import annotations

from api.utils.help_text import build_help_text
from api.utils.telegram import send_telegram_message

from .constants import WELCOME_TEXT


async def handle_start(chat_id: str) -> None:
    await send_telegram_message(chat_id, WELCOME_TEXT)


async def handle_help(chat_id: str) -> None:
    await send_telegram_message(chat_id, build_help_text(html=True))


async def handle_status(chat_id: str) -> None:
    await send_telegram_message(
        chat_id,
        "<b>LazyTube-Assistant</b>\n\n服務狀態：正常\n版本：v1.1.1",
    )


async def handle_my_id(chat_id: str, user_id: str) -> None:
    label = "個人 ID" if chat_id == user_id else "聊天室 ID"
    target = user_id if chat_id == user_id else chat_id
    await send_telegram_message(chat_id, f"<b>{label}</b>\n<code>{target}</code>")
