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
    print(f"🚀 LazyTube-Assistant [VERSION: 2026.03.06.21 - TEST MODE]")
    print(f"📂 當前目錄: {os.getcwd()}")
    print("="*50)

    # 1. 還原 NLM Cookie (增加長度診斷)
    cookie_b64_raw = os.environ.get("NLM_COOKIE_BASE64", "")
    if cookie_b64_raw:
        print("--- [ 正在分析 NLM 憑證字串 ] ---")
        print(f"📏 原始字串長度 (含空白/換行): {len(cookie_b64_raw)}")
        
        # 清理字串
        cookie_b64 = "".join(cookie_b64_raw.split())
        print(f"📏 清理後字串長度: {len(cookie_b64)}")
        
        try:
            cookie_data = base64.b64decode(cookie_b64)
            print(f"📦 解碼後數據大小: {len(cookie_data)} bytes")
            
            try:
                cookie_json = json.loads(cookie_data)
                print(f"✅ JSON 解析成功。欄位: {list(cookie_json.keys())}")
                if "cookies" in cookie_json:
                    cookies = cookie_json['cookies']
                    print(f"✅ 偵測到 {len(cookies)} 個 Cookie。")
                    # 印出所有 Cookie 的名稱以便排錯 (不印內容)
                    cookie_names = [c.get('name', 'UNKNOWN') for c in cookies]
                    print(f"🍪 Cookie 名稱清單: {', '.join(cookie_names)}")
                
                # 檢查 CSRF Token
                if cookie_json.get("csrf_token"):
                    print("✅ 偵測到 CSRF Token。")
                else:
                    print("⚠️ 警告: 找不到 CSRF Token。")
                
                # 寫入暫存檔
                temp_auth = os.path.abspath("temp_auth.json")
                with open(temp_auth, "wb") as f:
                    f.write(cookie_data)

                print(f"🔄 執行: nlm login --manual --profile default --force")
                login_proc = subprocess.run(
                    ["nlm", "login", "--manual", "--file", temp_auth, "--profile", "default", "--force"],
                    capture_output=True, text=True
                )
                if login_proc.returncode == 0:
                    print("✅ nlm login 成功！")
                else:
                    print(f"❌ nlm login 失敗: {login_proc.stdout} {login_proc.stderr}")
                
                if os.path.exists(temp_auth):
                    os.remove(temp_auth)
            except Exception as je:
                print(f"❌ JSON 格式錯誤 (可能被截斷): {je}")
                # 嘗試印出最後 20 個字元來確認是否結尾正確 (JSON 應以 } 結尾)
                try:
                    last_chars = cookie_data.decode('utf-8')[-20:]
                    print(f"🔍 數據結尾 20 字元: ...{last_chars}")
                except: pass
                
        except Exception as e:
            print(f"❌ 還原過程異常: {e}")

        print("--- [ NLM Doctor 診斷 ] ---")
        subprocess.run(["nlm", "doctor"], check=False)
        print("="*50)

    # --- [ 測試模式 ] ---
    print("🧪 測試模式啟動：跳過 YouTube API，使用固定測試 URL。")
    videos_to_process = [{
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "title": "TEST_VIDEO_SUMMARY",
        "channel": "TestChannel",
        "time": datetime.now(timezone.utc)
    }]

    for video in videos_to_process:
        summary = process_with_notebooklm(video["url"], video["title"])
        if summary:
            msg = (
                f"<b>🎥 {video['title']}</b>\n"
                f"📺 頻道：{video['channel']}\n"
                f"🔗 <a href='{video['url']}'>觀看影片</a>\n\n"
                f"📝 <b>AI 摘要</b>\n{summary}"
            )
            notify_telegram(msg)
            print(f"已完成並發送 Telegram 通知: {video['title']}")
            
    print("本次測試處理完成。")

if __name__ == "__main__":
    main()
