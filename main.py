import os
import sys
import json
import re
import base64
import subprocess
import uuid
import time
import requests
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
        print("錯誤: 缺少 YouTube API 環境變數")
        sys.exit(1)
    creds = Credentials(None, refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token",
                        client_id=client_id, client_secret=client_secret)
    if creds.expired: creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)

def get_last_check_time():
    if os.path.exists(LAST_CHECK_FILE):
        with open(LAST_CHECK_FILE, "r") as f:
            content = f.read().strip()
            if content: return datetime.fromisoformat(content)
    return datetime.now(timezone.utc) - timedelta(hours=1)

def save_last_check_time(dt):
    with open(LAST_CHECK_FILE, "w") as f:
        f.write(dt.isoformat())

def fetch_new_videos(youtube, last_check_time):
    print(f"正在檢查 {last_check_time.isoformat()} 之後的新影片...")
    new_videos = []
    try:
        subs_request = youtube.subscriptions().list(part="snippet,contentDetails", mine=True, maxResults=20, order="relevance")
        subs_response = subs_request.execute()
        for sub in subs_response.get("items", []):
            channel_id = sub["snippet"]["resourceId"]["channelId"]
            channel_title = sub["snippet"]["title"]
            activities_request = youtube.activities().list(part="snippet,contentDetails", channelId=channel_id, maxResults=5)
            activities_response = activities_request.execute()
            for item in activities_response.get("items", []):
                if item["snippet"]["type"] == "upload":
                    publish_time = datetime.fromisoformat(item["snippet"]["publishedAt"].replace("Z", "+00:00"))
                    if publish_time > last_check_time:
                        video_id = item.get("contentDetails", {}).get("upload", {}).get("videoId")
                        if video_id:
                            new_videos.append({"url": f"https://www.youtube.com/watch?v={video_id}", "title": item.get("snippet", {}).get("title", "Unknown"), "time": publish_time, "channel": channel_title})
                            print(f"發現新影片: {item.get('snippet', {}).get('title')} (來自 {channel_title})")
    except Exception as e: print(f"抓取影片錯誤: {e}")
    return sorted(new_videos, key=lambda x: x["time"])

def run_nlm(*args):
    home = os.path.expanduser("~")
    config_dir = os.path.join(home, ".notebooklm-mcp-cli")
    env = os.environ.copy()
    env["NLM_CONFIG_DIR"] = config_dir
    cmd = ["nlm", *args]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result

def process_with_notebooklm(video_url, title):
    print(f"正在處理: {title} ({video_url})")
    notebook_name = f"YT_{uuid.uuid4().hex[:4].upper()}"
    notebook_id = None
    summary_text = None
    try:
        # 1. 建立筆記本
        res = run_nlm("notebook", "create", notebook_name)
        if res.returncode == 0:
            match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
            notebook_id = match.group(1) if match else notebook_name
        else: return None
        
        # 2. 新增來源
        run_nlm("source", "add", notebook_id, "--url", video_url)
        
        # 3. 執行摘要 (使用驗證成功的語法)
        query = "請用繁體中文列出這部影片的 3 到 5 個核心重點，並加上影片標題"
        res = run_nlm("query", "notebook", notebook_id, query)
        
        if res.returncode == 0:
            # 處理可能含有的 JSON 格式
            try:
                data = json.loads(res.stdout)
                summary_text = data.get("value", {}).get("answer", res.stdout)
            except:
                summary_text = res.stdout.strip()
    finally:
        if notebook_id:
            run_nlm("notebook", "delete", notebook_id, "--confirm")
    return summary_text

def notify_telegram(message):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id: return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try: requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=15)
    except: pass

def main():
    print("="*50)
    print(f"🚀 LazyTube-Assistant [FINAL PRODUCTION VERSION]")
    print("="*50)

    # 1. 憑證精確注入
    cookie_b64_raw = os.environ.get("NLM_COOKIE_BASE64", "")
    if cookie_b64_raw:
        try:
            full_data_bytes = base64.b64decode("".join(cookie_b64_raw.split()))
            full_json = json.loads(full_data_bytes)
            home = os.path.expanduser("~")
            profile_dir = os.path.join(home, ".notebooklm-mcp-cli", "profiles", "default")
            os.makedirs(profile_dir, exist_ok=True)
            with open(os.path.join(profile_dir, "auth.json"), "wb") as f: f.write(full_data_bytes)
            with open(os.path.join(profile_dir, "cookies.json"), "w") as f: json.dump(full_json.get("cookies", []), f)
            with open(os.path.join(profile_dir, "metadata.json"), "w") as f: json.dump({k:v for k,v in full_json.items() if k!="cookies"}, f)
            with open(os.path.join(os.path.dirname(profile_dir), "..", "profiles.json"), "w") as f:
                json.dump({"default_profile": "default", "profiles": {"default": {}}}, f)
            print("✅ 憑證環境佈署成功。")
        except Exception as e: print(f"❌ 佈署失敗: {e}")

    # 2. 正式業務邏輯
    youtube = get_yt_service()
    last_check_time = get_last_check_time()
    new_videos = fetch_new_videos(youtube, last_check_time)
    
    if not new_videos:
        print("沒有發現新影片。")
        save_last_check_time(datetime.now(timezone.utc))
        return

    MAX_PER_RUN = int(os.environ.get("MAX_VIDEOS_PER_RUN", 5))
    for video in new_videos[:MAX_PER_RUN]:
        summary = process_with_notebooklm(video["url"], video["title"])
        if summary:
            msg = (f"<b>🎥 {video['title']}</b>\n"
                   f"📺 頻道：{video['channel']}\n"
                   f"🔗 <a href='{video['url']}'>觀看</a>\n\n"
                   f"📝 <b>AI 摘要</b>\n{summary}")
            notify_telegram(msg)
            print(f"✅ 已發送推播: {video['title']}")
        save_last_check_time(video["time"])
    print("本次處理完成。")

if __name__ == "__main__":
    main()
