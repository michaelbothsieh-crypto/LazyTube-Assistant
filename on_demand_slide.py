import sys
import os
import requests
from app.auth import AuthManager
from app.notebook import NotebookService
from app.notifier import Notifier
from app.config import Config

def main():
    if len(sys.argv) < 3:
        print("Usage: python on_demand_slide.py <url> <chat_id>")
        sys.exit(1)

    url = sys.argv[1]
    chat_id = sys.argv[2]
    message_id = os.environ.get("INPUT_MSG_ID")
    prompt = os.environ.get("INPUT_PROMPT") or "請用繁體中文列出這部影片或這個來源的 5 個核心重點，並在最後加上一句話的總結。"
    slide_format = os.environ.get("INPUT_FORMAT", "pdf")

    print(f"--- 🚀 隨選簡報生成任務啟動: {url} ---")
    print(f"📝 Prompt: {prompt}")
    print(f"📄 Format: {slide_format}")

    # 1. 認證環境佈署
    if not AuthManager.deploy_credentials():
        sys.exit(1)

    # 2. 處理影片並生成簡報
    nlm = NotebookService()

    pdf_path = nlm.process_slide(url, "On-Demand Slide", custom_prompt=prompt, slide_format=slide_format)

    if pdf_path and os.path.exists(pdf_path):
        # 3. 通知 (目前僅實作 Telegram 傳送檔案)
        print(f"📡 正在發送簡報至 {chat_id}...")
        
        caption = f"🎥 簡報已生成！\n🔗 來源：{url}"
        success = Notifier.send_document(target_chat_id=chat_id, file_path=pdf_path, caption=caption)
        
        if success:
            print("✅ 簡報發送成功")
        else:
            print("❌ 簡報發送失敗 (Notifier 回報失敗)")
    else:
        print("❌ 簡報生成流程失敗，未取得 PDF 檔案")
        sys.exit(1)
        
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
