import os
import json
import base64
import sys
import platform
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import requests

# 依賴檢查
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("❌ 缺少必要套件，請執行: pip install google-auth-oauthlib requests")
    sys.exit(1)

def get_nlm_path():
    """自動偵測 NLM 憑證路徑"""
    system = platform.system()
    home = os.path.expanduser("~")
    
    if system == "Windows":
        return os.path.join(os.environ.get("APPDATA", home), "notebooklm-mcp-cli", "profiles", "default")
    elif system == "Darwin": # Mac
        return os.path.join(home, "Library", "Application Support", "notebooklm-mcp-cli", "profiles", "default")
    else: # Linux
        return os.path.join(home, ".config", "notebooklm-mcp-cli", "profiles", "default")

def merge_nlm_cookies():
    """合併 NLM 憑證並轉為 Base64"""
    path = get_nlm_path()
    cookies_file = os.path.join(path, "cookies.json")
    metadata_file = os.path.join(path, "metadata.json")
    
    if not os.path.exists(cookies_file):
        # 嘗試舊路徑
        path = os.path.expanduser("~/.notebooklm-mcp-cli/profiles/default")
        cookies_file = os.path.join(path, "cookies.json")
        metadata_file = os.path.join(path, "metadata.json")

    if not os.path.exists(cookies_file):
        return None

    try:
        with open(cookies_file, 'r') as f: cookies = json.load(f)
        with open(metadata_file, 'r') as f: meta = json.load(f)
        meta['cookies'] = cookies
        combined = json.dumps(meta)
        return base64.b64encode(combined.encode()).decode()
    except:
        return None

def main():
    print("="*50)
    print("🤖 LazyTube-Assistant 全自動設定助手")
    print("="*50)
    
    # 1. YouTube OAuth
    print("\n[Step 1: YouTube API 授權]")
    client_id = input("請輸入 YouTube Client ID: ").strip()
    client_secret = input("請輸入 YouTube Client Secret: ").strip()
    
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    
    scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
    flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes)
    creds = flow.run_local_server(port=0)
    refresh_token = creds.refresh_token
    print("✅ YouTube 授權成功！")

    # 2. NLM Cookies
    print("\n[Step 2: NotebookLM 憑證偵測]")
    nlm_b64 = merge_nlm_cookies()
    if nlm_b64:
        print("✅ 成功偵測並合併 NLM 憑證！")
    else:
        print("⚠️ 找不到 NLM 憑證，請確保已執行過 nlm login --force")

    # 3. 產出 .env
    print("\n[Step 3: 產出設定檔案]")
    env_content = [
        f"YT_CLIENT_ID={client_id}",
        f"YT_CLIENT_SECRET={client_secret}",
        f"YT_REFRESH_TOKEN={refresh_token}",
        f"NLM_COOKIE_BASE64={nlm_b64 if nlm_b64 else 'YOUR_NLM_BASE64_HERE'}",
        "TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE",
        "TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE",
        "ALLOWED_USERS=YOUR_TG_ID_HERE"
    ]
    
    with open(".env", "w") as f:
        f.write("\n".join(env_content))
    
    print("="*50)
    print("🎉 設定完成！")
    print("請開啟專案目錄下的 .env 檔案，對照內容填入 GitHub Secrets。")
    print("="*50)

if __name__ == "__main__":
    main()
