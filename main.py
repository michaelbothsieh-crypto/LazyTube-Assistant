import os
import sys
import json
import re
import base64
import subprocess
import requests
import uuid
import platformdirs
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# 配置區域
LAST_CHECK_FILE = "last_check.txt"

def get_yt_service():
    """取得 YouTube API 服務"""
    client_id = os.environ.get("YT_CLIENT_ID")
    client_secret = os.environ.get("YT_CLIENT_SECRET")
    refresh_token = os.environ.get("YT_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        print("錯誤: 缺少 YouTube API 環境變數 (YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN)")
        sys.exit(1)
        
    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )
    
    if creds.expired:
        creds.refresh(Request())
        
    return build("youtube", "v3", credentials=creds)

def get_last_check_time():
    """讀取上次檢查的時間戳記"""
    if os.path.exists(LAST_CHECK_FILE):
        with open(LAST_CHECK_FILE, "r") as f:
            content = f.read().strip()
            if content:
                return datetime.fromisoformat(content)
    # 預設為 1 小時前
    return datetime.now(timezone.utc) - timedelta(hours=1)

def save_last_check_time(dt):
    """儲存本次檢查的時間戳記"""
    with open(LAST_CHECK_FILE, "w") as f:
        f.write(dt.isoformat())

def fetch_new_videos(youtube, last_check_time):
    """抓取訂閱頻道的最新影片"""
    print(f"正在檢查 {last_check_time.isoformat()} 之後的新影片...")
    
    new_videos = []
    
    try:
        # 1. 先取得你訂閱的頻道清單
        print("正在獲取訂閱頻道清單...")
        subs_request = youtube.subscriptions().list(
            part="snippet,contentDetails",
            mine=True,
            maxResults=20,
            order="relevance"
        )
        subs_response = subs_request.execute()
        
        for sub in subs_response.get("items", []):
            channel_id = sub["snippet"]["resourceId"]["channelId"]
            channel_title = sub["snippet"]["title"]
            
            # 2. 取得該頻道的最新動態
            activities_request = youtube.activities().list(
                part="snippet,contentDetails",
                channelId=channel_id,
                maxResults=5
            )
            activities_response = activities_request.execute()
            
            for item in activities_response.get("items", []):
                if item["snippet"]["type"] == "upload":
                    publish_time = datetime.fromisoformat(item["snippet"]["publishedAt"].replace("Z", "+00:00"))
                    
                    if publish_time > last_check_time:
                        video_id = item.get("contentDetails", {}).get("upload", {}).get("videoId")
                        if not video_id:
                            continue
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        title = item.get("snippet", {}).get("title", "Unknown")
                        new_videos.append({"url": video_url, "title": title, "time": publish_time, "channel": channel_title})
                        print(f"發現新影片: {title} (來自 {channel_title})")
                        
    except Exception as e:
        print(f"抓取影片時發生錯誤: {e}")
                
    return sorted(new_videos, key=lambda x: x["time"])

def process_with_notebooklm(video_url, title):
    """使用 nlm CLI 處理影片並生成摘要"""
    print(f"正在處理: {title} ({video_url})")
    notebook_name = f"YT_Summary_{uuid.uuid4().hex[:8].upper()}"

    def run_nlm(*args):
        cmd = ["nlm", *args]
        print(f"[CMD] {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            print(f"[STDOUT] {result.stdout[:500]}")
        if result.stderr:
            print(f"[STDERR] {result.stderr[:500]}")
        return result
    
    notebook_created = False
    summary_text = None
    
    try:
        # 1. 建立獨立 Notebook
        create_result = run_nlm("notebook", "create", notebook_name)
        if create_result.returncode == 0:
            notebook_created = True

        # 2. 新增來源
        add_result = run_nlm("source", "add", notebook_name, "--url", video_url)
        if add_result.returncode != 0:
            return None

        combined_output = add_result.stdout + add_result.stderr
        match = re.search(r"Source ID:\s*([a-zA-Z0-9\-]+)", combined_output)
        source_id = match.group(1) if match else None

        # 3. 執行查詢
        query = "請用繁體中文列出這部影片的 3 到 5 個核心重點，並加上影片標題"
        query_args = ["query", notebook_name, query]
        if source_id:
            query_args.extend(["-s", source_id])

        query_result = run_nlm(*query_args)
        if query_result.returncode == 0:
            summary_text = query_result.stdout.strip()

    finally:
        if notebook_created:
            run_nlm("notebook", "delete", notebook_name, "--confirm")

    return summary_text

def notify_telegram(message):
    """透過 Telegram Bot 推播摘要"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print(message)
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})

def main():
    print("="*50)
    print(f"🚀 LazyTube-Assistant [VERSION: 2026.03.06.24]")
    print(f"📂 當前目錄: {os.getcwd()}")
    print("="*50)

    # 1. 憑證佈署 (修正 profiles.json 格式)
    cookie_b64_raw = os.environ.get("NLM_COOKIE_BASE64", "")
    if cookie_b64_raw:
        print("--- [ 正在還原 NotebookLM 憑證環境 ] ---")
        cookie_data = base64.b64decode("".join(cookie_b64_raw.split()))
        home = os.path.expanduser("~")
        
        # 定義核心路徑
        base_dir = os.path.join(home, ".config", "notebooklm-mcp-cli")
        os.makedirs(base_dir, exist_ok=True)
        auth_path = os.path.join(base_dir, "auth.json")
        
        # 寫入正確格式的 profiles.json
        profiles_data = {
            "default_profile": "default",
            "profiles": {
                "default": {
                    "auth_file": auth_path
                }
            }
        }
        with open(os.path.join(base_dir, "profiles.json"), "w") as f:
            json.dump(profiles_data, f)
        
        # 寫入 auth.json 內容
        with open(auth_path, "wb") as f:
            f.write(cookie_data)
            
        # 同時佈署 profiles/default/ 結構以防萬一
        pd = os.path.join(base_dir, "profiles", "default")
        os.makedirs(pd, exist_ok=True)
        with open(os.path.join(pd, "auth.json"), "wb") as f:
            f.write(cookie_data)
            
        print("✅ 憑證與 Profile 結構佈署完成。")
        subprocess.run(["nlm", "doctor"], check=False)

    youtube = get_yt_service()
    last_check_time = get_last_check_time()
    new_videos = fetch_new_videos(youtube, last_check_time)
    
    if not new_videos:
        print("沒有發現新影片。")
        save_last_check_time(datetime.now(timezone.utc))
        return

    MAX_PER_RUN = int(os.environ.get("MAX_VIDEOS_PER_RUN", 5))
    videos_to_process = new_videos[:MAX_PER_RUN]
    
    print(f"發現 {len(new_videos)} 部影片，處理前 {len(videos_to_process)} 部。")

    for video in videos_to_process:
        summary = process_with_notebooklm(video["url"], video["title"])
        if summary:
            msg = (f"<b>🎥 {video['title']}</b>\n"
                   f"📺 頻道：{video['channel']}\n"
                   f"🔗 <a href='{video['url']}'>觀看</a>\n\n"
                   f"📝 <b>AI 摘要</b>\n{summary}")
            notify_telegram(msg)
        save_last_check_time(video["time"])
    print("本次處理完成。")

if __name__ == "__main__":
    main()
