import os
import sys
import logging
import json

# 加入專案根目錄到 path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.notebook import NotebookService
from app.notifier import Notifier
from app.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # 獲取 GitHub Actions 輸入
    urls_str = os.environ.get("URLS", "").strip()
    custom_prompt = os.environ.get("CUSTOM_PROMPT", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    message_id = os.environ.get("TELEGRAM_MESSAGE_ID", "").strip()

    if not urls_str or not chat_id:
        logger.error("缺少必要的參數：URLS 或 TELEGRAM_CHAT_ID")
        return

    urls = [u.strip() for u in urls_str.split(",") if u.strip()]
    
    print(f"🚀 開始批次處理 {len(urls)} 個網址...")
    
    nb_service = NotebookService()
    summary = nb_service.process_batch(urls, custom_prompt)

    if summary:
        # 發送結果
        Notifier.send_text(chat_id, summary)
        
        # 嘗試清理原本的「處理中」訊息
        if message_id:
            try:
                Notifier.delete_pending_message(chat_id, message_id)
            except:
                pass
    else:
        Notifier.send_text(chat_id, "❌ 批次摘要產出失敗，請稍後再試。")

if __name__ == "__main__":
    main()
