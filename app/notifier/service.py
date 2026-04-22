from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

from app.config import Config

from .cache_store import cache_file, cache_text
from .channels import is_line_chat
from .line_client import push_messages as push_line_messages
from .line_client import send_text as send_line_text
from .telegram_client import delete_message, send_document as send_telegram_document
from .telegram_client import send_photo as send_telegram_photo
from .telegram_client import send_text as send_telegram_text


class Notifier:
    @classmethod
    def send_summary(
        cls,
        title: str,
        url: str,
        channel: str,
        summary: str,
        target_chat_id: str | None = None,
    ) -> bool:
        chat_id = target_chat_id or Config.TG_CHAT_ID
        if not chat_id:
            return False

        message = f"📔 {title}\n📺 頻道：{channel}\n🔗 連結：{url}\n\n🤖 AI 摘要\n{summary}"
        return cls.send_text(chat_id, message)

    @classmethod
    def send_error(cls, target_chat_id: str, message: str, url: str | None = None) -> bool:
        text = f"❌ {message}"
        if url:
            text = f"{text}\n🔗 {url}"
        return cls.send_text(target_chat_id, text)

    @classmethod
    def send_text(cls, target_chat_id: str, text: str, html: bool = False) -> bool:
        chat_id = target_chat_id or Config.TG_CHAT_ID
        if not chat_id:
            return False

        if is_line_chat(chat_id):
            return send_line_text(chat_id, text)
        return send_telegram_text(chat_id, text, html=html)

    @classmethod
    def send_document(cls, target_chat_id: str, file_path: str, caption: str | None = None) -> bool:
        chat_id = target_chat_id or Config.TG_CHAT_ID
        if not chat_id:
            return False

        if is_line_chat(chat_id):
            proxy_url = cls.cache_report_to_redis(file_path)
            if not proxy_url:
                return False
            messages = []
            if caption:
                messages.append({"type": "text", "text": caption[:5000]})
            messages.append(
                {
                    "type": "text",
                    "text": f"檔案下載連結：{os.path.basename(file_path)}\n{proxy_url}",
                }
            )
            return push_line_messages(chat_id, messages)
        return send_telegram_document(chat_id, file_path, caption=caption)

    @classmethod
    def send_photo(cls, target_chat_id: str, file_path: str, caption: str | None = None) -> bool:
        chat_id = target_chat_id or Config.TG_CHAT_ID
        if not chat_id:
            return False

        if is_line_chat(chat_id):
            return cls.send_document(chat_id, file_path, caption=caption)
        return send_telegram_photo(chat_id, file_path, caption=caption)

    @staticmethod
    def delete_pending_message(chat_id: str, message_id: str | None) -> None:
        if not message_id or is_line_chat(chat_id):
            return
        try:
            delete_message(chat_id, str(message_id))
        except Exception as e:
            logger.warning("delete_pending_message failed chat=%s msg=%s: %s", chat_id, message_id, e)

    @staticmethod
    def cache_report_to_redis(file_path: str) -> Optional[str]:
        return cache_file(
            file_path,
            prefix="pdf_report",
            ttl_seconds=600,
            route="/api/pdf-proxy",
        )

    @staticmethod
    def cache_html_to_redis(html_content: str) -> Optional[str]:
        return cache_text(
            html_content,
            prefix="html_report",
            ttl_seconds=1800,
            route="/api/report-proxy",
        )

    @classmethod
    def send_report_link(cls, chat_id: str, html_content: str, caption: str) -> bool:
        proxy_url = cls.cache_html_to_redis(html_content)
        if not proxy_url:
            return False

        if is_line_chat(chat_id):
            return push_line_messages(
                chat_id,
                [
                    {"type": "text", "text": caption[:5000]},
                    {"type": "text", "text": f"完整報告連結：\n{proxy_url}\n\n(30 分鐘後過期)"},
                ],
            )
        return cls.send_text(chat_id, f"{caption}\n\n完整報告：{proxy_url}", html=False)

