"""
Telegram Bot API 工具函式
供 Vercel（立即回應）和 GitHub Actions（結果回呼）共用
"""
import os
import logging
import httpx

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


async def send_telegram_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """
    非同步發送 Telegram 訊息
    回傳 True 表示成功
    """
    if not BOT_TOKEN:
        logger.error("缺少 TELEGRAM_BOT_TOKEN 環境變數")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)

        if resp.status_code == 200:
            return True
        else:
            logger.error(f"Telegram API 錯誤：{resp.status_code} - {resp.text[:200]}")
            return False

    except Exception as e:
        logger.error(f"send_telegram_message 異常: {e}")
        return False
