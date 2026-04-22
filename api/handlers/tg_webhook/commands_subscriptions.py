from __future__ import annotations

import logging

from api.utils.github_dispatch import dispatch_group_workflow, dispatch_update_cron_workflow
from api.utils.telegram import send_telegram_message
from app.notifier import Notifier
from app.state_manager import StateManager
from app.subscription_vm import SubscriptionViewModel

from .parsing import parse_subscription_request
from .utils import extract_message_id

logger = logging.getLogger(__name__)


async def handle_sub(chat_id: str, text: str) -> None:
    url, prompt, preferred_time = parse_subscription_request(text)
    if not url:
        await send_telegram_message(chat_id, "用法：<code>/sub &lt;channel_url&gt; [prompt] [hour]</code>")
        return
    if prompt == "__INVALID_TIME__":
        await send_telegram_message(chat_id, "時間格式錯誤，請使用 0-23 小時。")
        return

    await StateManager.sync_from_blob("subscriptions.json")
    vm = SubscriptionViewModel()

    pending = await send_telegram_message(chat_id, "<b>正在建立訂閱</b>")
    pending_id = extract_message_id(pending)

    try:
        result = await vm.subscribe(chat_id, url, prompt, preferred_time)
        Notifier.delete_pending_message(chat_id, pending_id)

        await send_telegram_message(chat_id, result["message"])
        if not result["success"]:
            return

        await StateManager.sync_to_blob("subscriptions.json")
        await dispatch_group_workflow(chat_id)
    except Exception as exc:
        Notifier.delete_pending_message(chat_id, pending_id)
        logger.error("Subscription failed for %s: %s", chat_id, exc)
        await send_telegram_message(chat_id, "建立訂閱失敗，請稍後再試。")


async def handle_unsub(chat_id: str, text: str) -> None:
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await send_telegram_message(chat_id, "用法：<code>/unsub &lt;channel_id_or_index&gt;</code>")
        return

    await StateManager.sync_from_blob("subscriptions.json")
    vm = SubscriptionViewModel()
    result = await vm.unsubscribe(chat_id, parts[1])
    if result["success"]:
        await StateManager.sync_to_blob("subscriptions.json")
        await dispatch_update_cron_workflow()
    await send_telegram_message(chat_id, result["message"])


async def handle_list(chat_id: str) -> None:
    await StateManager.sync_from_blob("subscriptions.json")
    vm = SubscriptionViewModel()
    await send_telegram_message(chat_id, vm.list_subscriptions(chat_id))


async def handle_clear(chat_id: str) -> None:
    pending = await send_telegram_message(chat_id, "<b>正在清除全部訂閱</b>")
    pending_id = extract_message_id(pending)

    await StateManager.sync_from_blob("subscriptions.json")
    try:
        vm = SubscriptionViewModel()
        vm.clear_chat(chat_id)
        await StateManager.sync_to_blob("subscriptions.json")
    except Exception as exc:
        logger.error("Failed to clear subscriptions for %s: %s", chat_id, exc)
        await send_telegram_message(chat_id, "清除訂閱失敗，請稍後再試。")
        return

    StateManager.clear_local("subscriptions.json")
    Notifier.delete_pending_message(chat_id, pending_id)
    await send_telegram_message(chat_id, "已清除你的全部訂閱。")


