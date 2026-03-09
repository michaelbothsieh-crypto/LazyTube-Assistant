import sys
from datetime import datetime, timedelta, timezone
import os

from app.auth import AuthManager
from app.config import Config
from app.notebook import NotebookService
from app.notifier import Notifier
from app.youtube import YouTubeService


def get_last_check_time():
    """讀取上次檢查時間。"""
    try:
        if os.path.exists(Config.LAST_CHECK_FILE):
            with open(Config.LAST_CHECK_FILE, "r", encoding="utf-8") as file:
                return datetime.fromisoformat(file.read().strip())
    except Exception:
        pass
    # 狀態檔遺失或損壞時，回看最近 2 小時，避免一開始就漏掉。
    return datetime.now(timezone.utc) - timedelta(hours=2)


def save_check_time(check_time):
    """更新檢查時間。"""
    with open(Config.LAST_CHECK_FILE, "w", encoding="utf-8") as file:
        file.write(check_time.isoformat())


def get_processed_video_ids():
    """讀取近期已處理過的影片 ID (避免重複推播)。"""
    if not os.path.exists(Config.PROCESSED_VIDEOS_FILE):
        return set()
    try:
        with open(Config.PROCESSED_VIDEOS_FILE, "r", encoding="utf-8") as file:
            return {line.strip() for line in file if line.strip()}
    except Exception:
        return set()


def add_processed_video_id(video_id):
    """紀錄影片 ID 已處理，並保留最近 150 筆。"""
    ids = list(get_processed_video_ids())
    if video_id not in ids:
        ids.append(video_id)
    # 保留最近 150 筆記錄，以免無限增大
    trimmed_ids = ids[-150:]
    with open(Config.PROCESSED_VIDEOS_FILE, "w", encoding="utf-8") as file:
        for vid in trimmed_ids:
            file.write(f"{vid}\n")


def format_local_time(dt):
    """將時間轉成台北時間字串。"""
    return dt.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")


def main():
    import os
    print("=" * 50)
    print("LazyTube-Assistant [YouTube Summarizer Deduplication Fix]")
    print("=" * 50)

    # 1. 初始化
    if not AuthManager.deploy_credentials():
        print("憑證初始化失敗。")
        sys.exit(1)

    # 2. 獲取檢查參數
    yt = YouTubeService()
    last_check = get_last_check_time()
    current_time = datetime.now(timezone.utc)
    processed_ids = get_processed_video_ids()

    print(f"🕒 檢查區間：{format_local_time(last_check)} 到 {format_local_time(current_time)}")
    print(f"📦 已快取 ID 數：{len(processed_ids)}")

    # 3. 獲取新影片
    new_videos = yt.fetch_new_game_videos(last_check)
    if not new_videos:
        print("🔇 無新長影片，推進檢查點。")
        save_check_time(current_time)
        return

    # 4. 去重與篩選
    unique_to_process = []
    skipped_count = 0
    latest_video_time = last_check

    for v in new_videos:
        if v["video_id"] in processed_ids:
            skipped_count += 1
            latest_video_time = max(latest_video_time, v["time"])
            continue
        unique_to_process.append(v)

    if not unique_to_process:
        print(f"♻️ 發現 {len(new_videos)} 支影片，但全部皆為已重複項，跳過。")
        save_check_time(current_time)
        return

    # 5. 生成摘要與通知
    print(f"🚀 開始處理本輪 {len(unique_to_process)} 支新影片（限制 {Config.MAX_VIDEOS} 支）...")
    notebook = NotebookService()
    success_count = 0
    target_chat_id = sys.argv[1] if len(sys.argv) > 1 else None

    videos_batch = unique_to_process[:Config.MAX_VIDEOS]

    for video in videos_batch:
        print(f"🎬 處理中：{video['title']}")
        summary = notebook.process_video(video["url"], video["title"])
        if summary:
            # 發送通知
            Notifier.send_summary(
                video["title"], 
                video["url"], 
                video["channel"], 
                summary, 
                target_chat_id=target_chat_id
            )
            # 紀錄
            add_processed_video_id(video["video_id"])
            latest_video_time = max(latest_video_time, video["time"])
            success_count += 1
            print(f"✅ 完成：{video['title']}")
        else:
            print(f"⚠️ 略過：{video['title']} (生成失敗)")

    # 6. 更新狀態
    if success_count > 0 or skipped_count > 0:
        save_check_time(current_time)
        print(f"✨ 本輪總結：成功 {success_count} 支、略過重複 {skipped_count} 支。")
        print(f"🏁 檢查點更新至最新時間：{current_time.isoformat()}")
    else:
        print("🔚 無任何成功更新。")

if __name__ == "__main__":
    main()
