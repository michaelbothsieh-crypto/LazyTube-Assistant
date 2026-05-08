from __future__ import annotations

import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

from app.config import Config

from .cache_store import CacheStore
from .channels import is_line_chat
from .line_client import LineClient
from .telegram_client import TelegramClient, html_escape


def _make_tg() -> TelegramClient | None:
    return TelegramClient(Config.TG_BOT_TOKEN) if Config.TG_BOT_TOKEN else None


def _make_line() -> LineClient | None:
    return LineClient(Config.LINE_CHANNEL_ACCESS_TOKEN) if Config.LINE_CHANNEL_ACCESS_TOKEN else None


def _make_cache() -> CacheStore | None:
    if Config.REDIS_URL and Config.REDIS_TOKEN:
        return CacheStore(Config.REDIS_URL, Config.REDIS_TOKEN, Config.APP_BASE_URL)
    return None


def _strip_numeric_citations(text: str) -> str:
    if not text:
        return text
    return re.sub(r"\s*\[\d+(?:\s*(?:,|-)\s*\d+)*\]", "", text).strip()


class Notifier:
    _tg: TelegramClient | None = _make_tg()
    _line: LineClient | None = _make_line()
    _cache: CacheStore | None = _make_cache()

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
            return cls._line.send_text(chat_id, text) if cls._line else False
        return cls._tg.send_text(chat_id, text, html=html) if cls._tg else False

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
            messages.append({"type": "text", "text": f"檔案下載連結：{os.path.basename(file_path)}\n{proxy_url}"})
            return cls._line.push_messages(chat_id, messages) if cls._line else False
        return cls._tg.send_document(chat_id, file_path, caption=caption) if cls._tg else False

    @classmethod
    def send_photo(cls, target_chat_id: str, file_path: str, caption: str | None = None) -> bool:
        chat_id = target_chat_id or Config.TG_CHAT_ID
        if not chat_id:
            return False
        if is_line_chat(chat_id):
            return cls.send_document(chat_id, file_path, caption=caption)
        return cls._tg.send_photo(chat_id, file_path, caption=caption) if cls._tg else False

    @classmethod
    def send_photo_url(cls, target_chat_id: str, image_url: str, caption: str | None = None) -> bool:
        chat_id = target_chat_id or Config.TG_CHAT_ID
        if not chat_id or not image_url:
            return False
        if is_line_chat(chat_id):
            return cls._line.send_image_url(chat_id, image_url, caption=caption) if cls._line else False
        return cls._tg.send_photo_url(chat_id, image_url, caption=caption) if cls._tg else False

    @classmethod
    def send_video_url(cls, target_chat_id: str, video_url: str, caption: str | None = None) -> bool:
        chat_id = target_chat_id or Config.TG_CHAT_ID
        if not chat_id or not video_url:
            return False
        if is_line_chat(chat_id):
            return cls.send_text(chat_id, caption or "Threads 影片：公開頁面提供影片，但 LINE 需要可公開預覽圖才能直接推送影片。")
        return cls._tg.send_video_url(chat_id, video_url, caption=caption) if cls._tg else False

    @classmethod
    def delete_pending_message(cls, chat_id: str, message_id: str | None) -> None:
        if not message_id or is_line_chat(chat_id) or not cls._tg:
            return
        try:
            cls._tg.delete_message(chat_id, str(message_id))
        except Exception as e:
            logger.warning("delete_pending_message failed chat=%s msg=%s: %s", chat_id, message_id, e)

    @classmethod
    def cache_report_to_redis(cls, file_path: str) -> Optional[str]:
        """PDF 報告存 Redis，回傳代理 URL。"""
        if not cls._cache:
            return None
        return cls._cache.cache_file(
            file_path,
            prefix="pdf_report",
            ttl_seconds=Config.REDIS_PDF_TTL,
            route="/api/pdf-proxy",
        )

    @classmethod
    def cache_html_to_redis(cls, html_content: str) -> Optional[str]:
        """HTML 報告存 Redis，回傳代理 URL。"""
        if not cls._cache:
            return None
        return cls._cache.cache_text(
            html_content,
            prefix="html_report",
            ttl_seconds=Config.REDIS_HTML_TTL,
            route="/api/report-proxy",
        )

    @classmethod
    def send_report_link(
        cls,
        chat_id: str,
        html_content: str,
        caption: str,
        *,
        label: str = "",
        title: str = "",
        ep_date: str = "",
        preview: str = "",
    ) -> bool:
        """
        將 HTML 報告存入 Redis，發送摘要文字 + 可點擊 HTML 超連結。
        策略：caption 組成純文字（不含任何 HTML tag），
        僅最後加一個 <a href> 連結，與 /research 行為一致。
        """
        proxy_url = cls.cache_html_to_redis(html_content)
        if not proxy_url:
            return False
        return cls.send_cached_report_link(
            chat_id,
            proxy_url,
            caption,
            label=label,
            title=title,
            ep_date=ep_date,
            preview=preview,
        )

    @classmethod
    def send_cached_report_link(
        cls,
        chat_id: str,
        proxy_url: str,
        caption: str,
        *,
        label: str = "",
        title: str = "",
        ep_date: str = "",
        preview: str = "",
    ) -> bool:
        """發送已快取好的 HTML 報告連結。"""
        if not proxy_url:
            return False
        # 組純文字 caption（podcast 傳入欄位 / research 直接傳 caption）
        if label or title:
            # 清理標題：移除腳注符號 [1]、【】等避免混淆
            clean_title = _strip_numeric_citations(title)
            plain_caption = (
                f"🎙️ {label} 財經分析\n"
                f"📌 {clean_title}\n"
                f"📅 {ep_date}"
            )
            if preview:
                plain_caption += f"\n\n{_strip_numeric_citations(preview)}"
        else:
            plain_caption = caption

        # Line
        if is_line_chat(chat_id):
            plain = f"{plain_caption}\n\n完整報告：{proxy_url}"
            return cls._line.push_messages(chat_id, [
                {"type": "text", "text": plain[:5000]},
            ]) if cls._line else False

        # Telegram：純文字 + 唯一一個 <a> tag（最小化 HTML，最穩定）
        # 先把純文字部分 escape，然後拼接 <a> 連結
        safe_caption = html_escape(plain_caption)
        tg_msg = f'{safe_caption}\n\n📎 <a href="{proxy_url}">點此查看完整 HTML 報告</a>'
        return cls.send_text(chat_id, tg_msg, html=True)
