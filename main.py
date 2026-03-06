import os
import sys
import json
import re
import base64
import subprocess
import requests
import uuid
import platformdirs
import time
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# 配置區域
LAST_CHECK_FILE = "last_check.txt"

def get_yt_service():
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
    cmd = ["nlm", *args]
    print(f"[CMD] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout: print(f"[STDOUT] {result.stdout.strip()}")
    if result.stderr: print(f"[STDERR] {result.stderr.strip()}")
    return result

def process_with_notebooklm(video_url, title):
    print(f"正在處理: {title} ({video_url})")
    notebook_name = f"YT_Summary_{uuid.uuid4().hex[:8].upper()}"
    notebook_created = False
    summary_text = None
    try:
        res = run_nlm("notebook", "create", notebook_name)
        if res.returncode == 0: notebook_created = True
        else: return None
        
        res = run_nlm("source", "add", notebook_name, "--url", video_url)
        if res.returncode == 0:
            match = re.search(r"Source ID:\s*([a-zA-Z0-9\-]+)", res.stdout + res.stderr)
            source_id = match.group(1) if match else None
            query = "請用繁體中文列出這部影片的 3 到 5 個核心重點，並加上影片標題"
            q_args = ["query", notebook_name, query]
            if source_id: q_args.extend(["-s", source_id])
            res = run_nlm(*q_args)
            if res.returncode == 0: summary_text = res.stdout.strip()
    finally:
        if notebook_created: run_nlm("notebook", "delete", notebook_name, "--confirm")
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
    print(f"🚀 LazyTube-Assistant [VERSION: 2026.03.06.33]")
    print("="*50)

    # 1. 認證初始化 (調包計 3.0)
    cookie_b64_raw = os.environ.get("NLM_COOKIE_BASE64", "")
    if cookie_b64_raw:
        print("--- [ 正在執行終極認證調包 3.0 ] ---")
        try:
            cookie_data = base64.b64decode("".join(cookie_b64_raw.split()))
            temp_auth = os.path.abspath("temp_auth.json")
            with open(temp_auth, "wb") as f:
                f.write(cookie_data)

            # 步驟 A: 執行官方指令初始化目錄
            print("🔄 步驟 A: 執行官方指令初始化...")
            subprocess.run(
                ["nlm", "login", "--manual", "--file", temp_auth, "--profile", "default", "--force"],
                capture_output=True
            )
            
            # 步驟 B: 針對資料夾結構進行精確調包
            home = os.path.expanduser("~")
            config_dir = os.path.join(home, ".notebooklm-mcp-cli")
            # 在 0.4.0 中，憑證檔案在 profiles/default/auth.json
            final_auth = os.path.join(config_dir, "profiles", "default", "auth.json")
            
            os.makedirs(os.path.dirname(final_auth), exist_ok=True)
            with open(final_auth, "wb") as f:
                f.write(cookie_data)
            
            # 同時也寫入一份名為 'default' 的檔案，以防某些版本直接把檔名當成 profile 名稱
            alt_auth = os.path.join(config_dir, "profiles", "default", "default")
            with open(alt_auth, "wb") as f:
                f.write(cookie_data)

            print(f"✅ 步驟 B: 已成功調包，覆蓋完整憑證至 {final_auth}")

            if os.path.exists(temp_auth): os.remove(temp_auth)
            
            print("--- [ NLM 認證診斷 ] ---")
            run_nlm("doctor")
            print("="*50)
        except Exception as e:
            print(f"❌ 憑證佈署失敗: {e}")

    # 2. 業務邏輯
    youtube = get_yt_service()
    last_check_time = get_last_check_time()
    new_videos = fetch_new_videos(youtube, last_check_time)
    if not new_videos:
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
        save_last_check_time(video["time"])
    print("本次處理完成。")

if __name__ == "__main__":
    main()
