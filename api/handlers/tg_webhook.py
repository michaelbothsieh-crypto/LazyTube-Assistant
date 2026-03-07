"""
Telegram Webhook 處理器
- 解析 /nlm, /help, /status 指令
- 觸發 GitHub Actions workflow_dispatch
- 立即回 Telegram「處理中」訊息
"""
import os
import logging
import httpx
import re

from api.utils.github_dispatch import dispatch_nlm_workflow, dispatch_slide_workflow
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
    user_id = str(message.get("from", {}).get("id", ""))
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return

    # 2. 安全性檢查：白名單過濾
    allowed_raw = os.environ.get("ALLOWED_USERS", "").strip()
    if allowed_raw:
        allowed_list = [u.strip() for u in allowed_raw.split(",") if u.strip()]
        # 檢查發送者 (user_id) 或 聊天室 (chat_id) 是否在名單中
        if user_id not in allowed_list and chat_id not in allowed_list:
            # 只有當對方發送指令時才回覆權限不足，其餘閒聊不予理會
            if text.startswith("/"):
                await send_telegram_message(chat_id, f"⚠️ <b>權限不足</b>\n您的 ID (<code>{user_id}</code>) 不在授權名單中。")
            return
    else:
        # 重要：如果完全沒設定 ALLOWED_USERS，為了安全起見，預設拒絕所有外部指令 (除了 /start)
        # 除非您希望公開使用，否則請務必填寫 ID
        if not text.startswith("/start"):
            logger.warning("未設定 ALLOWED_USERS，已攔截潛在的未授權請求")
            return

    # 3. 處理群組指令格式 (e.g. /nlm@LazyTubeBot -> /nlm)
    if "@" in text:
        text = text.split("@")[0] if text.startswith("/") else text

    # --- 指令路由 ---
    if text.startswith("/start"):
        await _handle_start(chat_id)

    elif text.startswith("/my_id"):
        await send_telegram_message(chat_id, f"您的 Telegram ID 為：<code>{user_id}</code>")

    elif text.startswith("/help"):
        await _handle_help(chat_id)

    elif text.startswith("/status"):
        await _handle_status(chat_id)

    elif text.startswith("/nlm"):
        await _handle_nlm(chat_id, text)

    elif text.startswith("/slide"):
        await _handle_slide(chat_id, text)

    elif "youtube.com/" in text or "youtu.be/" in text:
        # 自動辨識網址 (若沒打指令但貼了網址)
        urls = re.findall(r'(https?://\S+)', text)
        if urls:
            await _handle_nlm(chat_id, f"/nlm {urls[0]}")

    else:
        # 非指令訊息，安靜地忽略，不留 Log
        return


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
        "<b>指令說明：</b> (問號?代表有預設值)\n"
        "📌 <code>/nlm &lt;url&gt; &lt;自訂Prompt?&gt;</code> (約1-3分鐘)\n"
        "  → 獲取來源的精華摘要\n\n"
        "📌 <code>/slide &lt;url&gt; &lt;自訂Prompt?&gt; &lt;語言?&gt; &lt;格式?&gt;</code> (約5-10分鐘)\n"
        "  → 產生 <b>繁體中文</b> PDF (預設) 或 PPTX 簡報\n"
        "  (💡 若要跳過 Prompt 直接指定語言/格式，Prompt 請輸入 <code>_</code>)\n\n"
        "<b>範例：</b>\n"
        "<code>/nlm https://youtu.be/xxxxx</code>\n"
        "<code>/slide https://youtu.be/xxxxx</code> (預設 PDF)\n"
        "<code>/slide https://youtu.be/xxxxx 著重架構 zh-TW pptx</code>\n"
        "<code>/slide https://youtu.be/xxxxx _ zh-TW pptx</code> (若不改 Prompt 可用 _ 代替)"
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

async def _handle_slide(chat_id: str, text: str):
    """
    解析 /slide 指令並觸發 GitHub Actions
    格式: /slide <url> [自訂prompt]
    """
    parts = text.split(maxsplit=2)  # ['/slide', '<url>', '<prompt(可選)>']

    # 驗證 URL
    if len(parts) < 2:
        await send_telegram_message(
            chat_id,
            "❌ <b>格式錯誤</b>\n使用方法：<code>/slide &lt;url&gt; [自訂Prompt]</code>"
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
        f"⏳ <b>已收到簡報生成任務，處理中...</b>\n\n"
        f"🔗 URL：<code>{url[:100]}</code>\n"
        f"📝 Prompt：{custom_prompt[:80]}{'...' if len(custom_prompt) > 80 else ''}\n\n"
        f"<i>NotebookLM 正在分析並生成簡報，完成後將自動回傳 PDF 檔案（約 1-3 分鐘）。</i>"
    )
    
    msg_id = ""
    if resp_data and resp_data.get("ok"):
        msg_id = str(resp_data.get("result", {}).get("message_id", ""))

    # 參數解析邏輯調整: /slide <url> <prompt?> <lang?> <format?>
    # 範例: /slide <url> "hello world" zh-TW pptx
    remaining_text = parts[2] if len(parts) >= 3 else ""
    
    slide_format = "pdf"
    slide_lang = "zh-TW"
    final_prompt = DEFAULT_PROMPT
    
    if remaining_text:
        # 簡單解析：尋找最後面的關鍵字
        sub_parts = remaining_text.rsplit(maxsplit=2)
        
        # 判斷最後一個是否為格式
        if len(sub_parts) >= 1 and sub_parts[-1].lower() in ["pdf", "pptx"]:
            slide_format = sub_parts[-1].lower()
            remaining_text = remaining_text.rsplit(maxsplit=1)[0] if len(sub_parts) > 1 else ""
            sub_parts = remaining_text.rsplit(maxsplit=1)
            
        # 判斷倒數第二個(或現在的最後一個)是否為語言代碼 (如 zh-TW, en, ja)
        lang_candidate = sub_parts[-1]
        if len(sub_parts) >= 1:
            is_lang = False
            if "-" in lang_candidate and len(lang_candidate) <= 6:
                is_lang = True
            elif len(lang_candidate) == 2 and lang_candidate.isalpha():
                is_lang = True
            
            if is_lang:
                slide_lang = lang_candidate
                remaining_text = remaining_text.rsplit(maxsplit=1)[0] if len(sub_parts) > 1 else ""
        
        # 剩下的就是 Prompt
        if remaining_text.strip() and remaining_text.strip() != "_":
            final_prompt = remaining_text.strip()

    # 觸發 GitHub Actions
    try:
        success = await dispatch_slide_workflow(
            url=url,
            prompt=final_prompt,
            chat_id=chat_id,
            message_id=msg_id,
            slide_format=slide_format,
            slide_lang=slide_lang  # 傳遞語言
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
        logger.error(f"dispatch_slide_workflow 發生錯誤: {e}")
        await send_telegram_message(
            chat_id,
            f"❌ <b>系統發生異常</b>\n\n"
            f"錯誤內容：<code>{str(e)[:100]}</code>\n"
            f"請聯繫管理員檢查 Vercel 日誌。"
        )
