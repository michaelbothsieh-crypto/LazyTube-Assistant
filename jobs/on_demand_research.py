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
        # 4. 生成並上傳 HTML 報告
        print("🎨 正在生成專業 HTML 報告...")
        html_content = Notifier.generate_html_report(topic, result)
        report_url = Notifier.upload_report(topic, html_content, chat_id)
        
        # 5. 回傳結果
        print("✅ 研究完成")
        
        # 提取前 300 字作為精簡摘要
        preview_text = result[:400] + "..." if len(result) > 400 else result
        
        report_msg = (
            f"🔎 <b>深度研究完成：{topic}</b>\n\n"
            f"📝 <b>核心摘要預覽：</b>\n{preview_text}\n\n"
        )
        
        if report_url:
            report_msg += f"🌐 <b>完整專業報告 (Web)：</b>\n<a href='{report_url}'>👉 點此線上瀏覽完整研究成果</a>\n"
        else:
            report_msg += f"⚠️ 報告上傳失敗，僅提供文字預覽。"
            
        Notifier.send_text(chat_id, report_msg, html=True)
    else:
        print(f"❌ 研究失敗: {result}")
        Notifier.send_text(chat_id, f"❌ 深度研究失敗: {result}", html=True)

if __name__ == "__main__":
    asyncio.run(main())
