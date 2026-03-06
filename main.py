import sys
from datetime import datetime, timezone
from app.config import Config
from app.auth import AuthManager
from app.youtube import YouTubeService
from app.notebook import NotebookService
from app.notifier import Notifier

def get_last_check_time():
    """讀取上次檢查時間"""
    try:
        with open(Config.LAST_CHECK_FILE, "r") as f:
            return datetime.fromisoformat(f.read().strip())
    except:
        return datetime.now(timezone.utc)

def save_check_time(dt):
    """更新檢查時間"""
    with open(Config.LAST_CHECK_FILE, "w") as f:
        f.write(dt.isoformat())

def main():
    print("="*50)
    print(f"🚀 LazyTube-Assistant [MODULAR VERSION]")
    print("="*50)

    # 1. 認證初始化
    if not AuthManager.deploy_credentials():
        print("❌ 憑證初始化失敗，中斷執行")
        sys.exit(1)

    # 2. 獲取新影片
    yt = YouTubeService()
    last_check = get_last_check_time()
    new_videos = yt.fetch_new_game_videos(last_check)
    
    if not new_videos:
        print("沒有發現感興趣的影片。")
        save_check_time(datetime.now(timezone.utc))
        return

    # 3. 處理摘要與通知
    nlm = NotebookService()
    process_count = 0
    
    # 支援從命令行參數讀取目標 Chat ID (隨選模式用)
    target_chat_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    for video in new_videos[:Config.MAX_VIDEOS]:
        # 呼叫時維持原樣，使用預設 Prompt
        summary = nlm.process_video(video["url"], video["title"])
        if summary:
            Notifier.send_summary(
                video["title"], 
                video["url"], 
                video["channel"], 
                summary, 
                target_chat_id=target_chat_id
            )
            print(f"✅ 已發送推播: {video['title']}")
            process_count += 1
        
        save_check_time(video["time"])
        
    print(f"本次處理完成，共產出 {process_count} 份摘要。")

if __name__ == "__main__":
    main()
