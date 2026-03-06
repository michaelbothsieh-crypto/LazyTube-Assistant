import sys
import os
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
    prompt = sys.argv[3] if len(sys.argv) > 3 else "請用繁體中文列出 5 個核心重點。"
    message_id = os.environ.get("INPUT_MSG_ID")

    print(f"--- 🚀 隨選摘要任務啟動: {url} ---")

    # 1. 認證
    if not AuthManager.deploy_credentials():
        sys.exit(1)

    # 2. 處理
    nlm = NotebookService()
    # 我們微調一下 NotebookService 讓它支援自定義 Prompt
    summary = nlm.process_video(url, "On-Demand Query") 
    # (註：目前 NotebookService 固定了 Prompt，我稍後會去微調它)

    if summary:
        # 3. 通知 (自動判斷 Telegram/LINE)
        Notifier.send_summary("隨選摘要結果", url, "手動觸發", summary, target_chat_id=chat_id)
        
        # 4. 刪除處理中訊息
        if message_id:
            import requests
            # 簡單實作刪除 (優先處理 Telegram)
            if not chat_id.startswith(('U', 'C', 'R')):
                requests.post(f"https://api.telegram.org/bot{Config.TG_BOT_TOKEN}/deleteMessage", 
                              json={"chat_id": chat_id, "message_id": message_id})

if __name__ == "__main__":
    main()
