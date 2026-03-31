import os
import sys
import logging
import json

# 加入專案根目錄到 path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.notebook import NotebookService
from app.notifier import Notifier
from app.config import Config
from app.auth import AuthManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # 獲取 GitHub Actions 輸入
    urls_str = os.environ.get("URLS", "").strip()
    custom_prompt = os.environ.get("CUSTOM_PROMPT", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    message_id = os.environ.get("TELEGRAM_MESSAGE_ID", "").strip()

    if not urls_str or not chat_id:
        logger.error("缺少必要的參數：URLS 或 TELEGRAM_CHAT_ID")
        return

    urls = [u.strip() for u in urls_str.split(",") if u.strip()]
    
    # 1. 預過濾 Shorts (如果網址中有 YouTube)
    from app.youtube import YouTubeService
    yt = YouTubeService()
    
    filtered_urls = []
    yt_video_ids = []
    url_to_vid = {}

    for u in urls:
        vid = None
        if "youtu.be/" in u:
            vid = u.split("youtu.be/")[1].split("?")[0]
        elif "youtube.com/watch" in u:
            import urllib.parse
            parsed = urllib.parse.urlparse(u)
            params = urllib.parse.parse_qs(parsed.query)
            vid = params.get("v", [None])[0]
        elif "youtube.com/shorts/" in u:
            vid = u.split("youtube.com/shorts/")[1].split("?")[0]
        
        if vid:
            yt_video_ids.append(vid)
            url_to_vid[u] = vid
        else:
            filtered_urls.append(u) # 非 YouTube 網址直接保留

    if yt_video_ids:
        details = yt._fetch_video_details(yt_video_ids)
        for u, vid in url_to_vid.items():
            duration = details["durations"].get(vid, 0)
            if duration > Config.SHORTS_MAX_SECONDS:
                filtered_urls.append(u)
            else:
                print(f"⚠️ 略過批次網址：偵測到影片為 Shorts ({u}, {duration}s)")

    if not filtered_urls:
        print("❌ 過濾後無有效網址可供處理。")
        Notifier.send_text(chat_id, "❌ 您提供的網址皆為 Shorts 短片，依據系統設定已略過處理。")
        if message_id:
            Notifier.delete_pending_message(chat_id, message_id)
        return

    print(f"🚀 開始批次處理 {len(filtered_urls)} 個網址 (已過濾 Shorts)...")
    
    # 部署認證
    if not AuthManager.deploy_credentials():
        logger.error("❌ 部署 NLM 認證失敗")
        return
    
    nb_service = NotebookService()
    summary = nb_service.process_batch(filtered_urls, custom_prompt)

    if summary:
        # 發送結果
        Notifier.send_text(chat_id, summary)
        
        # 嘗試清理原本的「處理中」訊息
        if message_id:
            try:
                Notifier.delete_pending_message(chat_id, message_id)
            except:
                pass
    else:
        Notifier.send_text(chat_id, "❌ 批次摘要產出失敗，請稍後再試。")

if __name__ == "__main__":
    main()
