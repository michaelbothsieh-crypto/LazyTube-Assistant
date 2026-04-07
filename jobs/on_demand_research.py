import sys
import os
import asyncio
import logging

# 加入根目錄到 path 以載入 app 模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.notebook import NotebookManager
from app.notifier import Notifier
from app.auth import setup_nlm_auth

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

async def main():
    if len(sys.argv) < 3:
        print("用法: python jobs/on_demand_research.py <主題> <chat_id> [msg_id]")
        return

    topic = sys.argv[1]
    chat_id = sys.argv[2]
    msg_id = sys.argv[3] if len(sys.argv) >= 4 else None

    print(f"--- 🔎 深度研究任務啟動: {topic} ---")
    
    # 1. 認證
    if not setup_nlm_auth():
        Notifier.send_text(chat_id, f"❌ 認證失敗，請檢查 NLM_COOKIE_BASE64。", html=True)
        return

    # 2. 執行研究 (使用 NotebookManager)
    nm = NotebookManager()
    
    # 在 NotebookManager 中新增一個 research_topic 方法
    success, result = await nm.research_topic(topic)
    
    # 3. 清理之前的提示訊息
    if msg_id:
        Notifier.delete_pending_message(chat_id, msg_id)

    if success:
        # 4. 回傳結果
        print("✅ 研究完成")
        report_text = f"🔎 <b>深度研究報告：{topic}</b>\n\n{result}"
        Notifier.send_text(chat_id, report_text, html=True)
    else:
        print(f"❌ 研究失敗: {result}")
        Notifier.send_text(chat_id, f"❌ 深度研究失敗: {result}", html=True)

if __name__ == "__main__":
    asyncio.run(main())
