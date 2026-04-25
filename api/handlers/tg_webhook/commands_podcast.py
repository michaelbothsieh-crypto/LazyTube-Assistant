"""
api/handlers/tg_webhook/commands_podcast.py

新增兩個 Podcast 相關指令：
  /subpodcast <url>  → 訂閱 Podcast RSS（自動解析平台 URL）
  /podcast           → 單次查詢，分析最新一集並立即回傳

/podcast 的實作策略：
  - 觸發 GitHub Actions (podcast-on-demand.yml)，以非同步方式執行
  - Actions 完成後透過現有 Notifier 機制回傳 TG 訊息
  - 這樣不會讓 webhook 逾時（Podcast 分析需要 5-15 分鐘）
"""
from __future__ import annotations

import logging

from api.utils.github_dispatch import GitHubActionManager
from api.utils.telegram import send_telegram_message
from app.podcast_rss_resolver import resolve_rss
from app.podcast_state import add_subscription, get_subscriptions, remove_subscription

from .utils import extract_message_id

logger = logging.getLogger(__name__)


async def handle_subpodcast(chat_id: str, text: str) -> None:
    """
    /subpodcast <url>  — 訂閱 Podcast RSS。

    支援平台：SoundOn、Firstory、Apple Podcasts、直接 RSS URL。
    """
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await send_telegram_message(
            chat_id,
            "用法：<code>/subpodcast &lt;podcast_url&gt;</code>\n\n"
            "支援 SoundOn、Firstory、Apple Podcasts 或直接 RSS URL。\n"
            "範例：<code>/subpodcast https://www.soundon.fm/podcasts/gooaye</code>",
        )
        return

    url = parts[1].strip()

    # 解析中訊息
    pending = await send_telegram_message(chat_id, f"🔍 正在解析 RSS：<code>{url[:80]}</code>")
    pending_id = extract_message_id(pending)

    rss_url, label = resolve_rss(url)

    # 刪除解析中訊息
    from app.notifier import Notifier
    Notifier.delete_pending_message(chat_id, pending_id)

    if not rss_url:
        await send_telegram_message(
            chat_id,
            f"❌ 無法從此 URL 找到 RSS Feed：\n<code>{url}</code>\n\n"
            "請嘗試直接貼上 RSS URL（.xml 結尾）。",
        )
        return

    # 寫入訂閱（podcast_state.json）
    # 注意：podcast 訂閱獨立於 YouTube 訂閱（subscriptions.json）
    added = add_subscription(rss_url, label)

    if not added:
        await send_telegram_message(
            chat_id,
            f"⚠️ 已訂閱過此頻道：<b>{label}</b>\n"
            f"<code>{rss_url}</code>",
        )
        return

    # 同步狀態到 GitHub state branch
    from app.state_manager import StateManager
    await StateManager.sync_to_blob("processed_podcasts.json")

    await send_telegram_message(
        chat_id,
        f"✅ <b>Podcast 訂閱成功！</b>\n\n"
        f"📻 頻道：<b>{label}</b>\n"
        f"🔗 RSS：<code>{rss_url}</code>\n\n"
        f"每天台北 09:00 自動分析最新集數並推送到此。",
    )


async def handle_unsubpodcast(chat_id: str, text: str) -> None:
    """
    /unsubpodcast <url_or_label> — 取消訂閱 Podcast。
    """
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        subs = get_subscriptions()
        if not subs:
            await send_telegram_message(chat_id, "目前沒有訂閱任何 Podcast。")
            return
        lines = [f"{i+1}. <b>{v['label']}</b>" for i, (k, v) in enumerate(subs.items())]
        await send_telegram_message(
            chat_id,
            "用法：<code>/unsubpodcast &lt;rss_url&gt;</code>\n\n"
            "目前訂閱清單：\n" + "\n".join(lines),
        )
        return

    target = parts[1].strip()
    subs = get_subscriptions()

    # 支援用序號取消
    if target.isdigit():
        idx = int(target) - 1
        if 0 <= idx < len(subs):
            target = list(subs.keys())[idx]
        else:
            await send_telegram_message(chat_id, f"❌ 序號 {target} 不存在，請用 /listpodcast 查詢。")
            return

    removed = remove_subscription(target)
    if not removed:
        await send_telegram_message(chat_id, f"❌ 找不到訂閱：<code>{target}</code>")
        return

    from app.state_manager import StateManager
    await StateManager.sync_to_blob("processed_podcasts.json")
    await send_telegram_message(chat_id, f"✅ 已取消 Podcast 訂閱：<code>{target}</code>")


async def handle_listpodcast(chat_id: str) -> None:
    """
    /listpodcast — 列出所有 Podcast 訂閱。
    """
    subs = get_subscriptions()
    if not subs:
        await send_telegram_message(
            chat_id,
            "目前沒有訂閱任何 Podcast。\n"
            "用 <code>/subpodcast &lt;url&gt;</code> 新增訂閱。",
        )
        return

    lines = []
    for i, (rss_url, info) in enumerate(subs.items(), 1):
        label = info.get("label", "未知頻道")
        added = info.get("added_at", "")[:10]
        lines.append(f"{i}. <b>{label}</b>\n   訂閱：{added}\n   <code>{rss_url}</code>")

    await send_telegram_message(
        chat_id,
        f"📻 <b>Podcast 訂閱清單（共 {len(subs)} 個）</b>\n\n" + "\n\n".join(lines),
    )


async def handle_podcast(chat_id: str, text: str) -> None:
    """
    /podcast [url] [集數]  — 單次查詢指定集數並立即分析回傳。
    /podcast list          — 列出各訂閱頻道的最新集數資訊。

    用法：
      /podcast                   → 最新一集（第1集）
      /podcast list              → 顯示各頻道最新 EP 資訊
      /podcast 655               → 搜尋 EP655
      /podcast <url>             → 指定頻道最新一集
      /podcast <url> 655         → 指定頻道 EP655

    不帶 url → 使用第一個訂閱頻道（或預設股癌）
    帶 url  → 臨時查詢，不寫入訂閱清單
    """
    parts = text.strip().split()
    args = parts[1:] if len(parts) > 1 else []

    # ── /podcast list ──────────────────────────────────────────────────
    if args and args[0].lower() == "list":
        subs = get_subscriptions()
        if not subs:
            await send_telegram_message(
                chat_id,
                "目前沒有訂閱任何 Podcast。\n用 <code>/subpodcast &lt;url&gt;</code> 新增訂閱。",
            )
            return

        import feedparser  # 延遲 import，避免影響非 list 路徑
        lines = []
        for rss_url, info in subs.items():
            label = info.get("label", "未知頻道")
            try:
                feed = feedparser.parse(rss_url)
                latest = feed.entries[0] if feed.entries else None
                if latest:
                    ep_title = latest.get("title", "無標題")[:60]
                    ep_date = latest.get("published", "")[:10]
                    lines.append(
                        f"📻 <b>{label}</b>\n"
                        f"   最新：{ep_title}\n"
                        f"   日期：{ep_date}"
                    )
                else:
                    lines.append(f"📻 <b>{label}</b>\n   ⚠️ RSS 無集數資料")
            except Exception:
                lines.append(f"📻 <b>{label}</b>\n   ❌ RSS 讀取失敗")

        await send_telegram_message(
            chat_id,
            f"🎙️ <b>Podcast 訂閱頻道最新集數（共 {len(subs)} 個）</b>\n\n"
            + "\n\n".join(lines)
            + "\n\n用 <code>/podcast &lt;集數&gt;</code> 查詢指定集數",
        )
        return
    # ──────────────────────────────────────────────────────────────────

    rss_url = ""
    episode_number = ""  # e.g. "655", 空字串 = 最新一集

    for arg in args:
        # 純數字視為集數編號（如 655）
        if arg.isdigit():
            episode_number = arg
        elif arg.startswith("http"):
            rss_url = arg

    # 若沒帶 URL，從訂閱清單取第一個
    if not rss_url:
        subs = get_subscriptions()
        if subs:
            rss_url = next(iter(subs))
        else:
            rss_url = "https://feeds.soundon.fm/podcasts/954689a5-3096-43a4-a80b-7810b219cef3.xml"

    # 若傳入的是頁面 URL 而非 RSS，嘗試解析
    if not rss_url.endswith(".xml") and "feeds." not in rss_url:
        resolved, _ = resolve_rss(rss_url)
        if resolved:
            rss_url = resolved

    episode_label = f"EP{episode_number}" if episode_number else "最新一集"

    pending = await send_telegram_message(
        chat_id,
        f"🎙️ <b>Podcast 即時分析已建立</b>\n\n"
        f"📻 集數：{episode_label}\n"
        f"🔗 RSS：<code>{rss_url[:80]}</code>\n\n"
        f"⏳ 預計需要 5-15 分鐘（含音檔下載 + AI 轉錄 + 財經分析），完成後自動推送。",
    )
    message_id = extract_message_id(pending)

    success = await GitHubActionManager.dispatch(
        "podcast-on-demand.yml",
        {
            "rss_url": rss_url,
            "mode": "latest",
            "episode_number": episode_number,  # 空字串 = 最新
            "chat_id": str(chat_id),
            "message_id": str(message_id),
        },
        timeout=10.0,
    )

    if not success:
        logger.error("podcast-on-demand dispatch failed for chat_id=%s", chat_id)
        await send_telegram_message(chat_id, "❌ 任務派送失敗，請稍後再試。")


