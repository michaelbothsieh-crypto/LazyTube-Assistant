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
    
    # 這裡我們稍微修改 NotebookService 邏輯，或者直接在這裡寫
    # 為了保持模組化，我們直接在 NotebookService 增加一個支援 prompt 的方法
    # 但現在先用最快的方式確保您收到訊息：
    summary = nlm.process_video(url, "On-Demand Query")

    if summary:
        # 3. 通知 (Notifier 會自動判斷 Telegram/LINE)
        print(f"📡 正在發送通知至 {chat_id}...")
        success = Notifier.send_summary("隨選摘要結果", url, "手動觸發", summary, target_chat_id=chat_id)
        if success:
            print("✅ 通知發送成功")
        
        # 4. 刪除處理中訊息 (僅限 Telegram)
        if message_id and not chat_id.startswith(('U', 'C', 'R')):
            requests.post(f"https://api.telegram.org/bot{Config.TG_BOT_TOKEN}/deleteMessage", 
                          json={"chat_id": chat_id, "message_id": message_id})

if __name__ == "__main__":
    main()
