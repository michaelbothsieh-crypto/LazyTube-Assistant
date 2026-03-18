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
import asyncio

from api.utils.github_dispatch import dispatch_nlm_workflow, dispatch_artifact_workflow
from api.utils.telegram import send_telegram_message
from api.utils.help_text import build_help_text
from api.utils.prompt_manager import get_optimized_prompt, get_nlm_prompt

logger = logging.getLogger(__name__)

# URL 長度上限 & Prompt 長度上限
_MAX_URL_LEN = 2048
_MAX_PROMPT_LEN = 500


def _validate_url(url: str) -> str | None:
    """驗證 URL，回傳錯誤訊息或 None 表示通過。"""
    if not url.startswith("http"):
        return f"❌ <b>無效的 URL</b>：<code>{url[:100]}</code>\n請提供完整的 http/https 網址。"
    if len(url) > _MAX_URL_LEN:
        return f"❌ URL 過長（上限 {_MAX_URL_LEN} 字元）。"
    return None




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
    # 注意：如果完全沒設定 ALLOWED_USERS，則視為公開使用，不進行攔截
    
    # 3. 處理群組指令格式 (e.g. /nlm@LazyTubeBot -> /nlm)
    if "@" in text:
        text = text.split("@")[0] if text.startswith("/") else text

    # --- 指令路由 ---
    if text.startswith("/start"):
        await _handle_start(chat_id)

    elif text.startswith("/my_id"):
        if chat_id == user_id:
            await send_telegram_message(chat_id, f"👤 <b>您的個人 ID</b>：<code>{user_id}</code>")
        else:
            await send_telegram_message(chat_id, f"💬 <b>此群組的 ID</b>：<code>{chat_id}</code>")

    elif text.startswith("/help"):
        await _handle_help(chat_id)

    elif text.startswith("/status"):
        await _handle_status(chat_id)

    elif text.startswith("/sub"):
        await _handle_sub(chat_id, text)

    elif text.startswith("/unsub"):
        await _handle_unsub(chat_id, text)

    elif text.startswith("/list"):
        await _handle_list(chat_id)

    elif text.startswith("/clear"):
        await _handle_clear(chat_id)

    elif text.startswith("/nlm"):
        await _handle_nlm(chat_id, text)

    elif text.startswith("/slide"):
        await _handle_slide(chat_id, text)

    elif text.startswith("/pic"):
        await _handle_pic(chat_id, text)

    elif text.startswith("/note"):
        await _handle_note(chat_id, text)

    elif text.startswith("/batch"):
        await _handle_batch(chat_id, text)

    else:
        # 非指令訊息，安靜地忽略，不留 Log
        return


async def _handle_start(chat_id: str):
    """回傳歡迎詞"""
    welcome_text = (
        "👋 <b>你好！我是 LazyTube 摘要助理</b>\n\n"
        "我可以幫你把冗長的 YouTube 影片或網頁內容，轉化為精簡的重點摘要。\n\n"
        "🚀 <b>快速開始：</b>\n"
        "直接輸入 <code>/nlm &lt;網址&gt;</code> 即可！\n\n"
        "使用 /help 查看更多進階指令。"
    )
    await send_telegram_message(chat_id, welcome_text)


async def _handle_help(chat_id: str):
    """回傳服務說明"""
    await send_telegram_message(chat_id, build_help_text(html=True))


async def _handle_status(chat_id: str):
    """回傳服務狀態"""
    await send_telegram_message(
        chat_id,
        "✅ <b>LazyTube-Assistant 服務正常運行中</b>\n"
        "版本：<code>v1.1.1</code>\n"
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
    url_err = _validate_url(url)
    if url_err:
        await send_telegram_message(chat_id, url_err)
        return

    custom_prompt = get_nlm_prompt(parts[2] if len(parts) >= 3 else "")
    if len(custom_prompt) > _MAX_PROMPT_LEN:
        custom_prompt = custom_prompt[:_MAX_PROMPT_LEN]

    # 立即回應「處理中」並取得 message_id
    resp_data = await send_telegram_message(
        chat_id,
        f"⏳ <b>已收到任務，處理中...</b>\n\n"
        f"🔗 URL：<code>{url[:100]}</code>\n"
        f"📝 Prompt：{custom_prompt[:80]}{'...' if len(custom_prompt) > 80 else ''}\n\n"
        f"<i>AI 正在分析，完成後將自動回傳結果（約 1-3 分鐘）。</i>"
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
            logger.error("dispatch_nlm_workflow failed: check GH_PAT_WORKFLOW, GH_REPO_OWNER, GH_REPO_NAME")
            await send_telegram_message(
                chat_id,
                "❌ <b>觸發任務失敗</b>\n\n"
                "原因：無法連接到後端服務。請聯繫管理員。"
            )
    except Exception as e:
        logger.error(f"dispatch_nlm_workflow 發生錯誤: {e}")
        await send_telegram_message(
            chat_id,
            "❌ <b>系統發生異常</b>\n\n"
            "請稍後重試，或聯繫管理員。"
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
    url_err = _validate_url(url)
    if url_err:
        await send_telegram_message(chat_id, url_err)
        return

    # 1. 參數解析與 Prompt 生成
    # 參數解析邏輯調整: /slide <url> <prompt?> <lang?> <format?>
    remaining_text = parts[2] if len(parts) >= 3 else ""
    
    slide_format = "pdf"
    slide_lang = "zh-TW"
    # 自動根據 URL 生成優化的預設 Prompt
    final_prompt = get_optimized_prompt(url)
    
    if remaining_text:
        # 簡單解析：尋找最後面的關鍵字
        sub_parts = remaining_text.rsplit(maxsplit=2)
        
        # 判斷最後一個是否為格式
        if len(sub_parts) >= 1 and sub_parts[-1].lower() in ["pdf", "pptx"]:
            slide_format = sub_parts[-1].lower()
            remaining_text = remaining_text.rsplit(maxsplit=1)[0] if len(sub_parts) > 1 else ""
            sub_parts = remaining_text.rsplit(maxsplit=1)
            
        # 判斷倒數第二個(或現在的最後一個)是否為語言代碼 (如 zh-TW, en, ja)
        if len(sub_parts) >= 1:
            lang_candidate = sub_parts[-1]
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

    # 2. 立即回應「處理中」並取得 message_id
    resp_data = await send_telegram_message(
        chat_id,
        f"<b>已收到簡報生成任務，正在處理中...</b>\n\n"
        f"URL：<code>{url[:100]}</code>\n"
        f"Prompt：{final_prompt[:80]}{'...' if len(final_prompt) > 80 else ''}\n\n"
        f"<i>AI 分析與簡報製作可能需要 5-10 分鐘，完成後將自動發送檔案。</i>"
    )
    
    msg_id = ""
    if resp_data and resp_data.get("ok"):
        msg_id = str(resp_data.get("result", {}).get("message_id", ""))

    # 觸發 GitHub Actions
    try:
        success = await dispatch_artifact_workflow(
            url=url,
            prompt=final_prompt,
            chat_id=chat_id,
            message_id=msg_id,
            slide_format=slide_format,
            slide_lang=slide_lang,
            artifact_type="slide_deck"
        )
        if not success:
            logger.error("dispatch_slide_workflow failed: check GH_PAT_WORKFLOW, GH_REPO_OWNER, GH_REPO_NAME")
            await send_telegram_message(
                chat_id,
                "❌ <b>觸發任務失敗</b>\n\n"
                "原因：無法連接到後端服務。請聯繫管理員。"
            )
    except Exception as e:
        logger.error(f"dispatch_slide_workflow 發生錯誤: {e}")
        await send_telegram_message(
            chat_id,
            "❌ <b>系統發生異常</b>\n\n"
            "請稍後重試，或聯繫管理員。"
        )

async def _handle_pic(chat_id: str, text: str):
    """解析 /pic 指令並生成圖片"""
    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        await send_telegram_message(chat_id, "❌ <b>格式錯誤</b>\n使用方法：<code>/pic &lt;url&gt; [自訂Prompt]</code>")
        return
    url, prompt = parts[1], get_nlm_prompt(parts[2] if len(parts) >= 3 else "")

    url_err = _validate_url(url)
    if url_err:
        await send_telegram_message(chat_id, url_err)
        return

    resp = await send_telegram_message(chat_id, f"⏳ <b>正在生成圖片總結...</b>\n🔗 URL: <code>{url[:60]}...</code>")
    msg_id = str(resp.get("result", {}).get("message_id", "")) if resp.get("ok") else ""

    try:
        success = await dispatch_artifact_workflow(url=url, prompt=prompt, chat_id=chat_id, message_id=msg_id, artifact_type="infographic")
        if not success:
            logger.error("dispatch_artifact_workflow (pic) failed")
            await send_telegram_message(chat_id, "❌ <b>觸發圖片任務失敗</b>\n請聯繫管理員。")
    except Exception as e:
        logger.error(f"dispatch_artifact_workflow (pic) error: {e}")
        await send_telegram_message(chat_id, "❌ <b>系統發生異常</b>\n請稍後重試。")

async def _handle_note(chat_id: str, text: str):
    """解析 /note 指令並生成報告"""
    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        await send_telegram_message(chat_id, "❌ <b>格式錯誤</b>\n使用方法：<code>/note &lt;url&gt; [自訂Prompt]</code>")
        return
    url, prompt = parts[1], get_nlm_prompt(parts[2] if len(parts) >= 3 else "")

    url_err = _validate_url(url)
    if url_err:
        await send_telegram_message(chat_id, url_err)
        return

    resp = await send_telegram_message(chat_id, f"⏳ <b>正在製作總結報告...</b>\n🔗 URL: <code>{url[:60]}...</code>")
    msg_id = str(resp.get("result", {}).get("message_id", "")) if resp.get("ok") else ""

    try:
        success = await dispatch_artifact_workflow(url=url, prompt=prompt, chat_id=chat_id, message_id=msg_id, artifact_type="report")
        if not success:
            logger.error("dispatch_artifact_workflow (note) failed")
            await send_telegram_message(chat_id, "❌ <b>觸發報告任務失敗</b>\n請聯繫管理員。")
    except Exception as e:
        logger.error(f"dispatch_artifact_workflow (note) error: {e}")
        await send_telegram_message(chat_id, "❌ <b>系統發生異常</b>\n請稍後重試。")


# --- 頻道訂閱指令處理 ---

async def _handle_sub(chat_id: str, text: str):
    """處理 /sub 指令"""
    from app.subscription_vm import SubscriptionViewModel
    from app.state_manager import StateManager
    from app.config import Config
    import re

    valid_hours = Config.VALID_PREFERRED_HOURS
    valid_hours_str = ", ".join(str(h) for h in valid_hours)

    parts = text.split()  # ['/sub', 'url', 'prompt...', 'time?']
    if len(parts) < 2:
        await send_telegram_message(
            chat_id,
            f"❌ <b>格式錯誤</b>\n"
            f"使用方法：<code>/sub &lt;頻道網址&gt; [客製化Prompt] [小時?]</code>\n\n"
            f"可用時段（台北時間）：<code>{valid_hours_str}</code>\n"
            f"範例：<code>/sub https://youtube.com/@... 10</code>"
        )
        return

    url = parts[1]
    custom_prompt = ""
    preferred_time = ""

    # 解析最後一個參數是否為小時
    if len(parts) >= 3:
        last_part = parts[-1]
        match = re.match(r"^(\d{1,2})(?::00)?$", last_part)
        if match:
            hour = int(match.group(1))
            if 0 <= hour <= 23:
                # 自動對齊到最近的有效時段
                preferred_time = SubscriptionViewModel.snap_preferred_time(hour)
                custom_prompt = get_nlm_prompt(" ".join(parts[2:-1]))
            else:
                await send_telegram_message(chat_id, "❌ <b>時間錯誤</b>\n小時請輸入 0 到 23 之間的數字。")
                return
        else:
            custom_prompt = get_nlm_prompt(" ".join(parts[2:]))

    # 先從 Blob 下載訂閱清單
    await StateManager.sync_from_blob("subscriptions.json")
    
    vm = SubscriptionViewModel()
    resp = await send_telegram_message(chat_id, "⏳ 正在分析頻道資訊並建立 GitHub 獨立排程...")
    msg_id = str(resp.get("result", {}).get("message_id", "")) if resp.get("ok") else ""
    
    try:
        # 執行訂閱 (這包含 GitHub API 呼叫)
        res = await vm.subscribe(chat_id, url, custom_prompt, preferred_time)
        
        # 只要執行完畢，無論成功失敗，第一時間嘗試刪除「⏳」訊息
        if msg_id:
            from app.notifier import Notifier
            Notifier.delete_pending_message(chat_id, msg_id)
            msg_id = "" # 防止重複刪除

        if res["success"]:
            # 關鍵：先將更新後的 subscriptions.json 上傳至 Blob
            await StateManager.sync_to_blob("subscriptions.json")
            
            # 刪除「處理中」訊息
            if msg_id:
                from app.notifier import Notifier
                Notifier.delete_pending_message(chat_id, msg_id)
                msg_id = ""

            # 發送成功訊息並取得其 ID
            resp_success = await send_telegram_message(chat_id, res["message"])
            success_msg_id = str(resp_success.get("result", {}).get("message_id", "")) if resp_success.get("ok") else ""
            
            if success_msg_id and res.get("channel_id"):
                vm.update_signup_msg_id(chat_id, res["channel_id"], success_msg_id)
                await StateManager.sync_to_blob("subscriptions.json")
            
            # 啟動 Action
            from api.utils.github_dispatch import dispatch_group_workflow
            await dispatch_group_workflow(chat_id)
        else:
            if msg_id:
                from app.notifier import Notifier
                Notifier.delete_pending_message(chat_id, msg_id)
            await send_telegram_message(chat_id, res["message"])

    except Exception as e:
        # 發生任何異常也要清理訊息
        if msg_id:
            from app.notifier import Notifier
            Notifier.delete_pending_message(chat_id, msg_id)
        logger.error(f"_handle_sub failed for {chat_id}: {e}")
        await send_telegram_message(chat_id, "❌ <b>設定失敗</b>\n請稍後重試，或聯繫管理員。")


async def _handle_unsub(chat_id: str, text: str):
    """處理 /unsub 指令"""
    from app.subscription_vm import SubscriptionViewModel
    from app.state_manager import StateManager

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await send_telegram_message(chat_id, "❌ <b>格式錯誤</b>\n使用方法：<code>/unsub &lt;序號或頻道ID&gt;</code>\n可用 <code>/list</code> 查看序號。")
        return

    await StateManager.sync_from_blob("subscriptions.json")
    vm = SubscriptionViewModel()
    res = await vm.unsubscribe(chat_id, parts[1])
    
    if res["success"]:
        # 關鍵：驗證雲端儲存是否成功
        ok = await StateManager.sync_to_blob("subscriptions.json")
        if ok:
            await send_telegram_message(chat_id, res["message"])
        else:
            await send_telegram_message(chat_id, "⚠️ <b>取消成功但雲端同步失敗</b>\n請稍後使用 <code>/list</code> 確認狀態。")
    else:
        await send_telegram_message(chat_id, res["message"])


async def _handle_list(chat_id: str):
    """處理 /list 指令"""
    from app.subscription_vm import SubscriptionViewModel
    from app.state_manager import StateManager

    await StateManager.sync_from_blob("subscriptions.json")
    vm = SubscriptionViewModel()
    msg = vm.list_subscriptions(chat_id)
    await send_telegram_message(chat_id, msg)


async def _handle_clear(chat_id: str):
    """處理 /clear 指令，強制移除該群組的所有訂閱紀錄"""
    from app.state_manager import StateManager
    from app.notifier import Notifier
    from app.config import Config
    import json
    import os

    resp = await send_telegram_message(chat_id, "🧹 正在強制清理訂閱紀錄...")
    msg_id = str(resp.get("result", {}).get("message_id", "")) if resp.get("ok") else ""
    
    # 2. 清理紀錄
    await StateManager.sync_from_blob("subscriptions.json")
    if os.path.exists(Config.SUBSCRIPTIONS_FILE):
        try:
            with open(Config.SUBSCRIPTIONS_FILE, "r") as f:
                subs = json.load(f)
            if chat_id in subs:
                del subs[chat_id]
                with open(Config.SUBSCRIPTIONS_FILE, "w") as f:
                    json.dump(subs, f)
                await StateManager.sync_to_blob("subscriptions.json")
        except Exception as e:
            logger.error(f"Failed to clear subscriptions for {chat_id}: {e}")
            await send_telegram_message(chat_id, "❌ 清理時發生錯誤，請稍後重試。")
            return
    
    # 強制移除本地快取，防止殘留
    StateManager.clear_local("subscriptions.json")

    # 刪除「處理中」訊息
    if msg_id:
        Notifier.delete_pending_message(chat_id, msg_id)

    await send_telegram_message(chat_id, "✅ 已成功移除該群組的所有訂閱紀錄。")


async def _handle_batch(chat_id: str, text: str):
    """
    解析 /batch 指令並觸發 GitHub Actions
    格式: /batch <url1, url2, ...> [自訂prompt]
    """
    from api.utils.github_dispatch import dispatch_batch_workflow
    import re

    # 1. 取得指令後的所有內容
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await send_telegram_message(
            chat_id,
            "❌ <b>格式錯誤</b>\n使用方法：<code>/batch &lt;網址1, 網址2,...&gt; [整合Prompt]</code>"
        )
        return

    content = parts[1]

    # 2. 使用正則表達式提取所有網址
    url_list = re.findall(r'https?://[^\s,()（）]+', content)
    
    if not url_list:
        await send_telegram_message(chat_id, "❌ <b>找不到有效網址</b>。")
        return

    if len(url_list) > 20:
        await send_telegram_message(chat_id, "⚠️ <b>網址過多</b>\n單次上限為 20 個，已截斷。")
        url_list = url_list[:20]

    # 3. 剩下的內容就是 Prompt
    custom_prompt_raw = content
    for u in url_list:
        custom_prompt_raw = custom_prompt_raw.replace(u, "")
    
    # 清理 Prompt 中殘留的逗號、括號與空格
    custom_prompt_raw = re.sub(r'^[ ,，()（）]+', '', custom_prompt_raw).strip()
    custom_prompt = get_nlm_prompt(custom_prompt_raw)

    # 4. 立即回應「處理中」
    resp_data = await send_telegram_message(
        chat_id,
        f"⏳ <b>已收到批次任務 ({len(url_list)} 個來源)</b>\n\n"
        f"正在啟動分析，完成後將回傳整合報告。"
    )
    
    msg_id = str(resp_data.get("result", {}).get("message_id", "")) if resp_data and resp_data.get("ok") else ""

    # 5. 觸發 Workflow
    success = await dispatch_batch_workflow(
        urls=",".join(url_list),
        prompt=custom_prompt,
        chat_id=chat_id,
        message_id=msg_id
    )
    
    if not success:
        await send_telegram_message(chat_id, "❌ <b>觸發批次任務失敗</b>。")
