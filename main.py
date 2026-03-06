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
        # 1. 先取得你訂閱的頻道清單 (最多取 20 個最近有活動的頻道)
        print("正在獲取訂閱頻道清單...")
        subs_request = youtube.subscriptions().list(
            part="snippet,contentDetails",
            mine=True,
            maxResults=20,
            order="relevance" # 或者用 alphabetical
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
                            print(f"警告：找不到 videoId，略過此項目 ({item.get('snippet', {}).get('title', 'Unknown')})")
                            continue
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        title = item.get("snippet", {}).get("title", "Unknown")
                        new_videos.append({"url": video_url, "title": title, "time": publish_time, "channel": channel_title})
                        print(f"發現新影片: {title} (來自 {channel_title})")
                        
    except Exception as e:
        print(f"抓取影片時發生錯誤: {e}")
                
    return sorted(new_videos, key=lambda x: x["time"])

def process_with_notebooklm(video_url, title):
    """使用 nlm CLI 處理影片並生成摘要，確保獨立性且在處理後刪除 Notebook"""
    print(f"正在處理: {title} ({video_url})")
    
    # 產生唯一的 Notebook 名稱
    notebook_name = f"YT_Summary_{uuid.uuid4().hex[:8].upper()}"

    def run_nlm(*args):
        """執行 nlm 指令並印出完整輸出（debug 用）"""
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
        print(f"正在建立獨立 Notebook: {notebook_name}...")
        create_result = run_nlm("notebook", "create", notebook_name)
        if create_result.returncode != 0:
            print(f"警告: Notebook 建立失敗，嘗試繼續...")
        else:
            notebook_created = True

        # 2. 新增來源並擷取 Source ID
        print("正在新增來源至 NotebookLM...")
        add_result = run_nlm("source", "add", notebook_name, "--url", video_url)
        if add_result.returncode != 0:
            print(f"新增來源失敗")
            return None

        # 用正規表達式從合併輸出截取 Source ID
        combined_output = add_result.stdout + add_result.stderr
        match = re.search(r"Source ID:\s*([a-zA-Z0-9\-]+)", combined_output)
        source_id = match.group(1) if match else None

        # 3. 執行查詢取得摘要
        query = "請用繁體中文列出這部影片的 3 到 5 個核心重點，並加上影片標題"
        print("正在產生摘要...")
        query_args = ["query", notebook_name, query]
        if source_id:
            query_args.extend(["-s", source_id])

        query_result = run_nlm(*query_args)

        if query_result.returncode == 0:
            summary_text = query_result.stdout.strip()
        else:
            print(f"查詢失敗")

    finally:
        # 4. 查完就刪除整個 Notebook，確保不遺留任何資料
        if notebook_created:
            print(f"清理中: 刪除臨時 Notebook {notebook_name}...")
            run_nlm("notebook", "delete", notebook_name, "--confirm")

    return summary_text

def notify_telegram(message):
    """透過 Telegram Bot 推播摘要，或在本地模式下印出至控制台"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("\n" + "="*30 + " [ 本地/Log 摘要輸出 ] " + "="*30)
        print(message)
        print("="*80 + "\n")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    resp = requests.post(url, json=payload)
    if resp.status_code != 200:
        print(f"Telegram 推播失敗: {resp.status_code} {resp.text}")

def main():
    print("="*50)
    print(f"🚀 LazyTube-Assistant [VERSION: 2026.03.06.14]")
    print(f"📂 當前目錄: {os.getcwd()}")
    print("="*50)

    # 1. 深度探查 notebooklm_tools (修正參數錯誤)
    print("--- [ 原始碼深度探查 ] ---")
    try:
        import notebooklm_tools
        pkg_dir = os.path.dirname(notebooklm_tools.__file__)
        print(f"📍 模組路徑: {pkg_dir}")
        
        # 搜尋包含關鍵字的文件內容
        print("🔍 搜尋路徑定義邏輯:")
        grep_proc = subprocess.run(
            ["grep", "-r", "-l", "profiles.json", pkg_dir],
            capture_output=True, text=True
        )
        for file_path in grep_proc.stdout.splitlines():
            print(f"📄 檔案: {file_path}")
            # 印出包含關鍵字的該行及其前後 3 行
            subprocess.run(["grep", "-C", "3", "profiles.json", file_path], check=False)
    except Exception as e:
        print(f"⚠️ 探查失敗: {e}")

    # 2. 還原 NLM Cookie (地毯式還原 3.0)
    cookie_b64 = os.environ.get("NLM_COOKIE_BASE64")
    if cookie_b64:
        print("--- [ 正在還原 NotebookLM 憑證 ] ---")
        cookie_data = base64.b64decode(cookie_b64)
        home = os.path.expanduser("~")
        
        # 增加更多可能的路徑變體
        possible_app_names = ["notebooklm-mcp-cli", "notebooklm-mcp", "notebooklm_mcp_cli"]
        for app_name in possible_app_names:
            for base in [os.path.join(home, ".config"), os.path.join(home, ".local", "share"), home]:
                base_dir = os.path.join(base, app_name if base != home else f".{app_name}")
                try:
                    os.makedirs(base_dir, exist_ok=True)
                    auth_path = os.path.join(base_dir, "auth.json")
                    with open(auth_path, "wb") as f:
                        f.write(cookie_data)
                    
                    profiles_path = os.path.join(base_dir, "profiles.json")
                    profiles_data = {"default_profile": "default", "profiles": {"default": {"auth_path": auth_path}}}
                    with open(profiles_path, "w") as f:
                        json.dump(profiles_data, f)
                    
                    # 同時建立 profiles/default/auth.json 結構
                    d_dir = os.path.join(base_dir, "profiles", "default")
                    os.makedirs(d_dir, exist_ok=True)
                    with open(os.path.join(d_dir, "auth.json"), "wb") as f:
                        f.write(cookie_data)
                except Exception:
                    pass

        # 3. 診斷
        print("--- [ NLM Doctor 診斷報告 ] ---")
        subprocess.run(["nlm", "doctor"], check=False)
        print("="*50)

    youtube = get_yt_service()
    last_check_time = get_last_check_time()
    
    new_videos = fetch_new_videos(youtube, last_check_time)
    
    if not new_videos:
        print("沒有發現新影片。")
        save_last_check_time(datetime.now(timezone.utc))
        return

    # 限制每次處理的數量，避免一次處理太多導致逾時或被封鎖
    # 優先從環境變數讀取，若無則預設為 5
    MAX_PER_RUN = int(os.environ.get("MAX_VIDEOS_PER_RUN", 5))
    videos_to_process = new_videos[:MAX_PER_RUN]
    remaining_count = len(new_videos) - MAX_PER_RUN
    
    print(f"發現 {len(new_videos)} 部新影片，本次將處理前 {len(videos_to_process)} 部。")

    for video in videos_to_process:
        summary = process_with_notebooklm(video["url"], video["title"])
        if summary:
            # 組合通知訊息 (Telegram 支援 HTML，用 <b> 加粗)
            msg = (
                f"<b>🎥 {video['title']}</b>\n"
                f"📺 頻道：{video['channel']}\n"
                f"🔗 <a href='{video['url']}'>觀看影片</a>\n\n"
                f"📝 <b>AI 摘要</b>\n{summary}"
            )
            notify_telegram(msg)
            print(f"已完成並發送 Telegram 通知: {video['title']}")
        
        # 每處理完一部就更新一次時間戳記，確保進度不遺失
        save_last_check_time(video["time"])
            
    if remaining_count > 0:
        print(f"還有 {remaining_count} 部影片待處理，將在下個小時的排程繼續。")
    print("本次處理完成。")

if __name__ == "__main__":
    main()
