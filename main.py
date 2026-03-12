import sys
from datetime import datetime, timedelta, timezone
import os

from app.auth import AuthManager
from app.config import Config
from app.notebook import NotebookService
from app.notifier import Notifier
from app.state_manager import StateManager
from app.youtube import YouTubeService


def format_local_time(dt):
    """將時間轉成台北時間字串。"""
    return dt.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")


def main():
    print("=" * 50)
    print("LazyTube-Assistant [YouTube Summarizer Deduplication Fix]")
    print("=" * 50)

    # 1. 驗證設定
    if not Config.validate():
        print("設定驗證失敗，請確認 GitHub Secrets 是否齊全。")
        sys.exit(1)

    # 2. 初始化憑證
    if not AuthManager.deploy_credentials():
        print("憑證初始化失敗。")
        sys.exit(1)

    # 3. 獲取檢查參數
    yt = YouTubeService()
    last_check = StateManager.get_last_check_time()
    current_time = datetime.now(timezone.utc)
    processed_ids = StateManager.get_processed_ids()

    print(f"🕒 檢查區間：{format_local_time(last_check)} 到 {format_local_time(current_time)}")
    print(f"📦 已快取 ID 數：{len(processed_ids)}")

    # 4. 獲取新影片
    new_videos = yt.fetch_new_game_videos(last_check)
    if not new_videos:
        print("🔇 無新長影片，推進檢查點。")
        StateManager.save_check_time(current_time)
        return

    # 5. 去重與篩選
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
        StateManager.save_check_time(current_time)
        return

    # 6. 生成摘要與通知
    print(f"🚀 開始處理本輪 {len(unique_to_process)} 支新影片（限制 {Config.MAX_VIDEOS} 支）...")
    notebook = NotebookService()
    success_count = 0
    target_chat_id = sys.argv[1] if len(sys.argv) > 1 else None

    videos_batch = unique_to_process[:Config.MAX_VIDEOS]

    for video in videos_batch:
        print(f"🎬 處理中：{video['title']}")
        summary = notebook.process_video(video["url"], video["title"])
        if summary:
            Notifier.send_summary(
                video["title"],
                video["url"],
                video["channel"],
                summary,
                target_chat_id=target_chat_id
            )
            StateManager.add_processed_id(video["video_id"])
            latest_video_time = max(latest_video_time, video["time"])
            success_count += 1
            print(f"✅ 完成：{video['title']}")
        else:
            print(f"⚠️ 略過：{video['title']} (生成失敗)")

    # 7. 更新狀態
    if success_count > 0 or skipped_count > 0:
        StateManager.save_check_time(current_time)
        print(f"✨ 本輪總結：成功 {success_count} 支、略過重複 {skipped_count} 支。")
        print(f"🏁 檢查點更新至最新時間：{current_time.isoformat()}")
    else:
        print("🔚 無任何成功更新。")


if __name__ == "__main__":
    main()
