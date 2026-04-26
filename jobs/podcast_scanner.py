"""
podcast_scanner.py — 每日定時掃描 Podcast RSS，上傳 NLM 取得財經分析，推送 Telegram。

環境變數：
  PODCAST_RSS_URLS   : 逗號分隔 RSS（優先於訂閱清單）
  CUSTOM_PROMPT      : prompt 關鍵字（預設 "finance"）
  PODCAST_MODE       : "daily"（新集數）| "latest"（只取最新一集，on-demand 用）
  PODCAST_CHAT_ID    : on-demand 指定回傳的 chat_id
  PODCAST_MESSAGE_ID : on-demand 的 pending message id
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

import feedparser
import requests

# ── 確保 project root 在 path ──────────────────────────────────────────────
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.auth import AuthManager
from app.config import Config
from app.notebook.notebook_session import NotebookSession
from app.notebook.parsing import parse_query_output
from app.notebook.runner import NotebookRunner
from app.notifier.reporting import generate_podcast_html_report
from app.notifier.service import Notifier
from app.podcast_state import get_subscriptions, init_empty, is_processed, mark_processed
from api.utils.prompt_manager import get_nlm_prompt

MAX_EPISODES_PER_RUN = 2
DOWNLOAD_TIMEOUT_SEC = 300
MP3_SIZE_LIMIT_MB = 200


# ── RSS 掃描 ──────────────────────────────────────────────────────────────

def fetch_new_episodes(
    rss_url: str,
    mode: str = "daily",
    chat_id: str = "",
    episode_number: str = "",
) -> list[dict]:
    """
    掃描單一 RSS，回傳待處理的集數。
    mode="latest" + episode_number 空  → 取最新一集
    mode="latest" + episode_number="655" → 在 title 中搜尋含 "655" 的集數
    mode="daily"  → 以 (rss_url, chat_id) 為複合 key 過濾已處理 GUID
    """
    print(f"📡 揉描 RSS：{rss_url}")
    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        print(f"  ⚠️  RSS 解析失敗：{e}")
        return []

    episodes = []
    for entry in feed.entries:
        guid = entry.get("id") or entry.get("link", "")
        if not guid:
            continue
        audio_url = _extract_audio_url(entry)
        if not audio_url:
            continue
        episodes.append({
            "guid": guid,
            "title": entry.get("title", "未知集數"),
            "audio_url": audio_url,
            "published": entry.get("published", ""),
            "rss_url": rss_url,
        })

    if not episodes:
        return []

    if mode == "latest":
        if episode_number:
            # 在 title 中搜尋符合集數編號的集數
            matched = [
                ep for ep in episodes
                if episode_number in ep["title"].replace(" ", "")
                or f"EP{episode_number}" in ep["title"].upper()
                or f"EP {episode_number}" in ep["title"].upper()
                or f"第{episode_number}集" in ep["title"]
            ]
            if matched:
                print(f"  ✅ 找到集數 {episode_number}：{matched[0]['title']}")
                return [matched[0]]
            # RSS 有可能只列出近期集數，找不到時提示
            print(f"  ⚠️  找不到集數 {episode_number}（RSS 僅包含最近 {len(episodes)} 集），改取最新一集")
        return [episodes[0]]

    # daily：以 (rss_url, chat_id) 為複合 key 去重
    new = [ep for ep in episodes if not is_processed(rss_url, ep["guid"], chat_id)]
    print(f"  ✅ 新集數：{len(new)} / {len(episodes)}")
    return new


def _extract_audio_url(entry) -> str | None:
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("audio"):
            return enc.get("href") or enc.get("url")
    for link in getattr(entry, "links", []):
        if link.get("type", "").startswith("audio"):
            return link.get("href")
    return None


# ── 音檔下載 ──────────────────────────────────────────────────────────────

def download_audio(audio_url: str, title: str, max_retries: int = 2) -> str | None:
    """
    下載音檔到暫存檔。失敗最多重試 max_retries 次，間隔 10 秒。
    """
    suffix = ".m4a" if "m4a" in audio_url.lower() else ".mp3"
    for attempt in range(1, max_retries + 2):  # 1 .. max_retries+1
        label = f" (第 {attempt} 次嘗試)" if attempt > 1 else ""
        print(f"  ⬇️  下載音檔：{title}{label}")
        try:
            resp = requests.get(audio_url, timeout=DOWNLOAD_TIMEOUT_SEC, stream=True)
            resp.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp_path = tmp.name
                size_mb = 0
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    tmp.write(chunk)
                    size_mb += len(chunk) / (1024 * 1024)
                    if size_mb > MP3_SIZE_LIMIT_MB:
                        os.remove(tmp_path)
                        print(f"  ⚠️  超過 {MP3_SIZE_LIMIT_MB}MB，跳過")
                        return None
            print(f"  ✅ 下載完成：{size_mb:.1f}MB")
            return tmp_path
        except Exception as e:
            print(f"  ❌ 下載失敗：{e}")
            if attempt <= max_retries:
                print("     10 秒後重試...")
                time.sleep(10)
    return None



# ── NLM 分析 ──────────────────────────────────────────────────────────────

def analyze_with_nlm(runner: NotebookRunner, mp3_path: str, prompt: str) -> str | None:
    with NotebookSession(runner, "POD") as session:
        if not session.ready():
            print("  ❌ 無法建立 NotebookLM notebook")
            return None
        print(f"  📓 Notebook：{session.notebook_id}")
        print("  ⏳ 上傳音檔等待轉錄...")
        result = runner.run(
            "source", "add", session.notebook_id,
            "--file", mp3_path, "--wait", verbose=True,
        )
        if result.returncode != 0:
            print(f"  ❌ 上傳失敗：{result.stderr}")
            return None
        print("  ✅ 轉錄完成，開始 query...")
        qr = runner.run("query", "notebook", session.notebook_id, prompt)
        if qr.returncode != 0:
            print(f"  ❌ query 失敗：{qr.stderr}")
            return None
        return parse_query_output(qr.stdout)


# ── 推送：HTML 報告 + Redis 連結 ────────────────────────────────

def send_podcast_report(
    title: str,
    analysis: str,
    published: str,
    label: str = "Podcast",
    chat_id: str = "",
    message_id: str = "",
) -> bool:
    """
    將分析文字生成精美 HTML 報告，存入 Redis，發送 TG 摘要 + 連結。
    若 Redis 未設定，則 fallback 為純文字推送（誅於 4096 字）。
    """
    target_chat = chat_id or Config.TG_CHAT_ID
    if not target_chat:
        print("  ⚠️  未設定 TG 憑證，跳過")
        return False

    # 將 pending 訊息刪除
    if message_id:
        Notifier.delete_pending_message(target_chat, message_id)

    # 生成 HTML
    print("  🎨 生成 HTML 報告...")
    html_content = generate_podcast_html_report(
        ep_title=title,
        ep_date=published[:10] if published else "",
        channel_label=label,
        analysis=analysis,
    )

    # 摘要文字（前 200 字）
    import re as _re
    clean = _re.sub(r"【.*?】", "", analysis).strip()
    preview = (clean[:200] + "…") if len(clean) > 200 else clean
    caption = (
        f"🎙️ <b>{label} 財經分析</b>\n"
        f"📌 {title}\n"
        f"📅 {published[:10] if published else ''}"
        f"\n\n{preview}"
    )

    # 嘗試發送 HTML 報告連結
    success = Notifier.send_report_link(target_chat, html_content, caption)
    if success:
        print("  ✅ HTML 報告推送成功")
        return True

    # Fallback：發送純文字
    print("  ⚠️  Redis 未設定，改用純文字推送")
    plain = f"🎙️ {label} 財經分析\n📌 {title}\n📅 {published}\n\n{analysis}"
    if len(plain) > 4096:
        plain = plain[:4090] + "…"
    return Notifier.send_text(target_chat, plain, html=False)


# ── 主流程 ────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 55)
    print("🎙️  Podcast 財經分析掃描器")
    print("=" * 55)

    if not AuthManager.deploy_credentials():
        print("❌ NLM 憑證初始化失敗")
        sys.exit(1)

    init_empty()

    mode = os.environ.get("PODCAST_MODE", "daily")
    on_demand_chat = os.environ.get("PODCAST_CHAT_ID", "")
    on_demand_msg = os.environ.get("PODCAST_MESSAGE_ID", "")
    episode_number = os.environ.get("PODCAST_EPISODE_NUMBER", "").strip()  # e.g. "655"
    prompt_key = os.environ.get("CUSTOM_PROMPT", "podcast")  # 預設使用 podcast 專屬 prompt
    prompt = get_nlm_prompt(prompt_key)
    print(f"📝 模式：{mode}  Prompt：{prompt_key}  集數：{episode_number or '最新'}")

    # RSS 來源優先順序：環境變數 > 訂閱清單
    # 兩者皆空時不執行（不再 fallback 預設頻道，避免未訂閱也自動推送）
    rss_env = os.environ.get("PODCAST_RSS_URLS", "").strip()
    if rss_env:
        rss_sources = [(u.strip(), "") for u in rss_env.split(",") if u.strip()]
    else:
        subs = get_subscriptions()
        if subs:
            rss_sources = [(url, info.get("label", "")) for url, info in subs.items()]
        else:
            print("ℹ️  無 RSS 來源且無訂閱清單，結束。")
            print("   使用 /subpodcast <url> 訂閱後即可自動推送。")
            return

    runner = NotebookRunner()
    total_success = 0

    for rss_url, label in rss_sources:
        episodes = fetch_new_episodes(
            rss_url, mode=mode, chat_id=on_demand_chat, episode_number=episode_number
        )
        if not episodes:
            print(f"🔚 [{label or rss_url[:40]}] 無新集數")
            continue

        to_process = episodes[:1] if mode == "latest" else episodes[:MAX_EPISODES_PER_RUN]

        for ep in to_process:
            print(f"\n{'─' * 50}")
            print(f"📻 {ep['title']}  [{ep['published']}]")
            mp3_path = None
            try:
                mp3_path = download_audio(ep["audio_url"], ep["title"])
                if not mp3_path:
                    continue

                analysis = analyze_with_nlm(runner, mp3_path, prompt)
                if not analysis:
                    print("  ❌ NLM 分析失敗")
                    continue

                send_podcast_report(
                    title=ep["title"],
                    analysis=analysis,
                    published=ep["published"],
                    label=label or "Podcast",
                    chat_id=on_demand_chat,
                    message_id=on_demand_msg,
                )
                on_demand_msg = ""  # 已刪，避免安全網重複刪


                # daily 模式才記錄已處理；
                # 使用 on_demand_chat 作為 chat_id key：
                #   - 排程（daily， on_demand_chat="")：用空字串 key，全域排程不重複
                #   - on-demand（latest mode）：不寫入，下次返回同一集也可再查
                if mode == "daily":
                    mark_processed(rss_url, ep["guid"], chat_id=on_demand_chat)
                total_success += 1

            except Exception as e:
                print(f"  ❌ 例外：{e}")
            finally:
                if mp3_path and os.path.exists(mp3_path):
                    os.remove(mp3_path)

            if ep != to_process[-1]:
                time.sleep(30)

    print(f"\n{'=' * 55}")
    print(f"✨ 完成：成功 {total_success} 集")
    print("=" * 55)

    # 安全網：無論成功或失敗，確保 pending 訊息一定被刪除
    # （正常推送後 send_to_telegram 內部已刪，這裡是決關保障）
    if on_demand_chat and on_demand_msg:
        bot_token = Config.TG_BOT_TOKEN
        if bot_token:
            try:
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/deleteMessage",
                    json={"chat_id": on_demand_chat, "message_id": int(on_demand_msg)},
                    timeout=10,
                )
            except Exception:
                pass  # 已刪或不存在，忽略


if __name__ == "__main__":
    main()
