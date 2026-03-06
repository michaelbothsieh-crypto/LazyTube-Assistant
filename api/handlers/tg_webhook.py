"""
Telegram Webhook 處理器
- 解析 /nlm, /help, /status 指令
- 觸發 GitHub Actions workflow_dispatch
- 立即回 Telegram「處理中」訊息
"""
import os
import logging
import httpx

from api.utils.github_dispatch import dispatch_nlm_workflow
from api.utils.telegram import send_telegram_message

logger = logging.getLogger(__name__)

# 預設 Prompt（若用戶未提供）
DEFAULT_PROMPT = "請用繁體中文列出這部影片或這個來源的 5 個核心重點，並在最後加上一句話的總結。"




async def handle_telegram_update(update: dict):
    """解析並路由 Telegram Update"""
    # 1. 處理被加入群組的事件
    message = update.get("message")
    if message and "new_chat_members" in message:
        for member in message["new_chat_members"]:
            # 檢查加入的是否為機器人自己
            if member.get("is_bot") and "lazytube" in member.get("username", "").lower():
                chat_id = str(message["chat"]["id"])
                await _handle_start(chat_id)
                return

    if not message:
        logger.info("收到非 message 類型的 update，略過")
        return

    chat_id = str(message.get("chat", {}).get("id", ""))
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return

    # 2. 處理群組指令格式 (e.g. /nlm@LazyTubeBot -> /nlm)
    if "@" in text:
        text = text.split("@")[0] if text.startswith("/") else text

    # --- 指令路由 ---
    if text.startswith("/start"):
        await _handle_start(chat_id)

    elif text.startswith("/help"):
        await _handle_help(chat_id)

    elif text.startswith("/status"):
        await _handle_status(chat_id)

    elif text.startswith("/nlm"):
        await _handle_nlm(chat_id, text)

    else:
        # 非指令訊息，忽略
        logger.info(f"收到非指令訊息，略過: {text[:50]}")


async def _handle_start(chat_id: str):
    """回傳歡迎詞"""
    welcome_text = (
        "👋 <b>你好！我是 LazyTube 摘要助理</b>\n\n"
        "我可以幫你把冗長的 YouTube 影片或網頁內容，透過 Google NotebookLM 轉化為精簡的重點摘要。\n\n"
        "🚀 <b>快速開始：</b>\n"
        "直接輸入 <code>/nlm &lt;網址&gt;</code> 即可！\n\n"
        "使用 /help 查看更多進階指令。"
    )
    await send_telegram_message(chat_id, welcome_text)


async def _handle_help(chat_id: str):
    """回傳使用說明"""
    help_text = (
        "🤖 <b>LazyTube NotebookLM 查詢機器人</b>\n\n"
        "<b>指令說明：</b>\n"
        "📌 <code>/nlm &lt;url&gt;</code>\n"
        "  → 使用預設 Prompt 生成摘要\n\n"
        "📌 <code>/nlm &lt;url&gt; &lt;自訂Prompt&gt;</code>\n"
        "  → 使用自訂 Prompt 查詢\n\n"
        "📌 <code>/status</code>\n"
        "  → 查看服務狀態\n\n"
        "<b>範例：</b>\n"
        "<code>/nlm https://youtu.be/xxxxx</code>\n"
        "<code>/nlm https://youtu.be/xxxxx 列出所有技術術語和定義</code>"
    )
    await send_telegram_message(chat_id, help_text)


async def _handle_status(chat_id: str):
    """回傳服務狀態"""
    await send_telegram_message(
        chat_id,
        "✅ <b>LazyTube-Assistant 服務正常運行中</b>\n"
        "使用 /help 查看可用指令。"
    )


async def _handle_nlm(chat_id: str, text: str):
    """
    解析 /nlm 指令並觸發 GitHub Actions
    格式: /nlm <url> [自訂prompt]
    """
    parts = text.split(maxsplit=2)  # ['/nlm', '<url>', '<prompt(可選)>']

    # 驗證 URL
    if len(parts) < 2:
        await send_telegram_message(
            chat_id,
            "❌ <b>格式錯誤</b>\n使用方法：<code>/nlm &lt;url&gt; [自訂Prompt]</code>"
        )
        return

    url = parts[1]
    if not url.startswith("http"):
        await send_telegram_message(
            chat_id,
            f"❌ <b>無效的 URL</b>：<code>{url[:100]}</code>\n請提供完整的 http/https 網址。"
        )
        return

    # URL 長度限制
    if len(url) > 2048:
        await send_telegram_message(chat_id, "❌ URL 過長（上限 2048 字元）。")
        return

    # 自訂 Prompt（選填，最多 500 字）
    custom_prompt = parts[2] if len(parts) >= 3 else DEFAULT_PROMPT
    if len(custom_prompt) > 500:
        custom_prompt = custom_prompt[:500]
        logger.info("自訂 Prompt 超過 500 字元，已截斷")

    # 立即回應「處理中」並取得 message_id
    resp_data = await send_telegram_message(
        chat_id,
        f"⏳ <b>已收到任務，處理中...</b>\n\n"
        f"🔗 URL：<code>{url[:100]}</code>\n"
        f"📝 Prompt：{custom_prompt[:80]}{'...' if len(custom_prompt) > 80 else ''}\n\n"
        f"<i>NotebookLM 正在分析，完成後將自動回傳結果（約 1-3 分鐘）。</i>"
    )
    
    msg_id = ""
    if resp_data and resp_data.get("ok"):
        msg_id = str(resp_data.get("result", {}).get("message_id", ""))

    # 觸發 GitHub Actions
    try:
        success = await dispatch_nlm_workflow(
            url=url,
            prompt=custom_prompt,
            chat_id=chat_id,
            message_id=msg_id
        )
        if not success:
            debug_info = f"Auth:{'Yes' if os.environ.get('GH_PAT_WORKFLOW') else 'No'} | Repo:{os.environ.get('GH_REPO_NAME')}"
            await send_telegram_message(
                chat_id,
                f"❌ <b>觸發任務失敗</b>\n\n"
                f"原因：無法連接到 GitHub API。\n"
                f"🔧 <b>除錯資訊</b>：<code>{debug_info}</code>\n"
                f"請檢查 Vercel 環境變數設定是否正確。"
            )
    except Exception as e:
        logger.error(f"dispatch_nlm_workflow 發生錯誤: {e}")
        await send_telegram_message(
            chat_id,
            f"❌ <b>系統發生異常</b>\n\n"
            f"錯誤內容：<code>{str(e)[:100]}</code>\n"
            f"請聯繫管理員檢查 Vercel 日誌。"
        )
