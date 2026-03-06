import sys
import os
import requests
from app.auth import AuthManager
from app.notebook import NotebookService
from app.notifier import Notifier
from app.config import Config

def main():
    if len(sys.argv) < 3:
        print("Usage: python on_demand.py <url> <chat_id> [prompt]")
        sys.exit(1)

    url = sys.argv[1]
    chat_id = sys.argv[2]
    prompt = sys.argv[3] if len(sys.argv) > 3 else "請用繁體中文列出 5 個核心重點，並加上影片標題。"
    message_id = os.environ.get("INPUT_MSG_ID")

    print(f"--- 🚀 隨選摘要任務啟動: {url} ---")

    # 1. 認證環境佈署
    if not AuthManager.deploy_credentials():
        sys.exit(1)

    # 2. 執行摘要 (使用 NotebookService)
    nlm = NotebookService()
    
    # 將自定義 Prompt 傳遞給處理方法
    summary = nlm.process_video(url, "On-Demand Query", custom_prompt=prompt)

    if summary:
        # 3. 通知 (Notifier 會自動判斷 Telegram/LINE)
        print(f"📡 正在發送通知至 {chat_id}...")
        success = Notifier.send_summary("隨選摘要結果", url, "手動觸發", summary, target_chat_id=chat_id)
        if success:
            print("✅ 通知發送成功")
        
        # 4. 刪除處理中訊息 (僅限 Telegram)
        if message_id and not chat_id.startswith(('U', 'C', 'R')):
            print(f"🗑️ 正在嘗試刪除 Telegram 訊息 ID: {message_id}")
            del_url = f"https://api.telegram.org/bot{Config.TG_BOT_TOKEN}/deleteMessage"
            try:
                # Telegram API 要求 message_id 為整數
                del_resp = requests.post(del_url, json={
                    "chat_id": chat_id, 
                    "message_id": int(message_id)
                }, timeout=10)
                if del_resp.status_code == 200:
                    print("✅ 訊息刪除成功")
                else:
                    print(f"⚠️ 訊息刪除失敗: {del_resp.status_code} {del_resp.text}")
            except Exception as de:
                print(f"❌ 刪除訊息發生異常: {de}")

if __name__ == "__main__":
    main()
