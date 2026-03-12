import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

def debug_auth():
    print("="*50)
    print("🔍 YouTube API 認證診斷工具")
    print("="*50)

    # 嘗試從環境變數或 .env 讀取
    client_id = os.environ.get("YT_CLIENT_ID")
    client_secret = os.environ.get("YT_CLIENT_SECRET")
    refresh_token = os.environ.get("YT_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        # 嘗試讀取本地 .env
        try:
            from dotenv import load_dotenv
            load_dotenv()
            client_id = os.environ.get("YT_CLIENT_ID")
            client_secret = os.environ.get("YT_CLIENT_SECRET")
            refresh_token = os.environ.get("YT_REFRESH_TOKEN")
        except ImportError:
            pass

    if not all([client_id, client_secret, refresh_token]):
        print("❌ 錯誤：找不到必要的環境變數。")
        print("請確保您在 GitHub Secrets 或本地 .env 檔案中正確設定了以下變數：")
        print("- YT_CLIENT_ID")
        print("- YT_CLIENT_SECRET")
        print("- YT_REFRESH_TOKEN")
        return

    print(f"ID: {client_id[:5]}...{client_id[-5:]}")
    print(f"Secret: 已設定")
    print(f"Refresh Token: {refresh_token[:5]}...{refresh_token[-5:]}")

    try:
        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )

        print("\n正在嘗試刷新 Token...")
        creds.refresh(Request())
        print("✅ Token 刷新成功！您的憑證目前有效。")
        
        # 測試一下 API
        youtube = build("youtube", "v3", credentials=creds)
        response = youtube.channels().list(part="snippet", mine=True).execute()
        channel_name = response["items"][0]["snippet"]["title"]
        print(f"👤 成功連結至頻道：{channel_name}")

    except Exception as e:
        print(f"\n❌ 刷新失敗！")
        error_msg = str(e)
        print(f"詳細錯誤：{error_msg}")
        
        if "invalid_grant" in error_msg:
            print("\n💡 診斷建議：")
            print("1. 檢查 Google Cloud Console 中的『OAuth 同意畫面』內容。")
            print("2. 檢查『發佈狀態 (Publishing Status)』是否為『測試 (Testing)』。")
            print("   - 如果是測試中，Token 會在 7 天後過期。")
            print("   - 建議點擊『發佈應用程式 (PUBLISH APP)』使 Token 永久有效。")
            print("3. 或者，您可能在 Google 帳號設定移除過該應用程式。")
        elif "invalid_client" in error_msg:
            print("\n💡 診斷建議：Client ID 或 Client Secret 錯誤。")

if __name__ == "__main__":
    debug_auth()
