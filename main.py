import sys
from datetime import datetime, timedelta, timezone

from app.auth import AuthManager
from app.config import Config
from app.notebook import NotebookService
from app.notifier import Notifier
from app.youtube import YouTubeService


def get_last_check_time():
    """讀取上次檢查時間。"""
    try:
        with open(Config.LAST_CHECK_FILE, "r", encoding="utf-8") as file:
            return datetime.fromisoformat(file.read().strip())
    except Exception:
        # 狀態檔遺失時，回看最近 2 小時，避免直接漏掉最新影片。
        return datetime.now(timezone.utc) - timedelta(hours=2)


def save_check_time(check_time):
    """更新檢查時間。"""
    with open(Config.LAST_CHECK_FILE, "w", encoding="utf-8") as file:
        file.write(check_time.isoformat())


def format_local_time(dt):
    """將時間轉成台北時間字串。"""
    return dt.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")


def main():
    print("=" * 50)
    print("LazyTube-Assistant [模組化版本]")
    print("=" * 50)

    # 1. 認證初始化
    if not AuthManager.deploy_credentials():
        print("部署憑證建立失敗，程式結束。")
        sys.exit(1)

    # 2. 取得本輪檢查區間
    yt = YouTubeService()
    last_check = get_last_check_time()
    current_time = datetime.now(timezone.utc)

    print(
        "本輪檢查區間："
        f"{format_local_time(last_check)} 到 {format_local_time(current_time)}（台北時間）"
    )
    print(f"上次檢查時間（UTC）：{last_check.isoformat()}")
    print(f"本次執行時間（UTC）：{current_time.isoformat()}")

    # 3. 抓取新影片
    new_videos = yt.fetch_new_game_videos(last_check)
    if not new_videos:
        print("本輪沒有找到新的長影片，保持原有檢查時間。")
        return

    # 4. 產生摘要並通知
    notebook = NotebookService()
    process_count = 0
    
    # 紀錄最新成功處理的影片時間
    latest_processed_time = last_check

    # 支援從命令列參數傳入目標 Chat ID（隨選模式用）
    target_chat_id = sys.argv[1] if len(sys.argv) > 1 else None

    # 只處理 Config 中限制的數量
    videos_to_process = new_videos[: Config.MAX_VIDEOS]
    
    for video in videos_to_process:
        summary = notebook.process_video(video["url"], video["title"])
        if summary:
            Notifier.send_summary(
                video["title"],
                video["url"],
                video["channel"],
                summary,
                target_chat_id=target_chat_id,
            )
            print(f"已發送摘要：{video['title']}")
            process_count += 1
            # 只有當摘要成功生成並發送後，才視為這個時間點已被「完整處理」
            latest_processed_time = video["time"]
        else:
            # 如果失敗（例如 API 超時），我們下次還想再試一次這支影片
            # 所以不更新 latest_processed_time，迴圈繼續
            print(f"摘要生成失敗，跳過影片：{video['title']}，下次將重試。")

    # 5. 更新檢查時間
    if latest_processed_time > last_check:
        save_check_time(current_time)
        print(f"更新檢查時間至：{current_time.isoformat()}")
    else:
        print("本輪無新影片或處理失敗，保持原有檢查時間。")

    print(f"本輪完成，成功處理 {process_count} 支影片。")


if __name__ == "__main__":
    main()
