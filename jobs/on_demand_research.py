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
    msg_id = sys.argv[3] if len(sys.argv) >= 4 and sys.argv[3] != "" else None
    mode = sys.argv[4] if len(sys.argv) >= 5 else "fast"

    print(f"--- 🔎 深度研究任務啟動: {topic} (模式: {mode}) ---")
    
    # 1. 認證
    if not setup_nlm_auth():
        Notifier.send_text(chat_id, f"❌ 認證失敗，請檢查 NLM_COOKIE_BASE64。", html=True)
        return

    # 2. 執行研究 (使用 NotebookManager)
    nm = NotebookManager()
    
    success, result = await nm.research_topic(topic, mode=mode)
    
    # 3. 清理之前的提示訊息
    if msg_id:
        Notifier.delete_pending_message(chat_id, msg_id)

    if success:
        # 4. 生成 HTML 內容
        print("🎨 正在生成專業 HTML 報告...")
        html_content = Notifier.generate_html_report(topic, result)
        
        is_line = str(chat_id).startswith(("U", "C", "R"))
        report_url = None
        
        if is_line:
            print("📄 正在為 LINE 用戶生成 PDF 報告...")
            pdf_path = Notifier.generate_pdf_report(html_content)
            if pdf_path:
                report_url = Notifier.upload_report(topic, html_content, chat_id, file_path=pdf_path)
                # 清理 PDF 暫存
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
        
        # 如果不是 Line 或者 PDF 生成失敗，則使用 HTML 流程
        if not report_url:
            report_url = Notifier.upload_report(topic, html_content, chat_id)
        
        # 5. 回傳結果
        print("✅ 研究完成")
        
        # 提取摘要預覽
        preview_text = result[:400] + "..." if len(result) > 400 else result
        
        file_ext = "PDF" if is_line and report_url and ".pdf" in report_url else "Web"
        
        if report_url:
            report_msg = (
                f"🔎 <b>深度研究完成：{topic}</b>\n\n"
                f"📝 <b>核心摘要預覽：</b>\n{preview_text}\n\n"
                f"🌐 <b>完整專業報告 ({file_ext})：</b>\n<a href='{report_url}'>👉 點此線上瀏覽完整研究成果</a>\n"
            )
            Notifier.send_text(chat_id, report_msg, html=True)
        else:
            # 備援方案
            report_msg = (
                f"🔎 <b>深度研究完成：{topic}</b>\n\n"
                f"📝 <b>核心摘要預覽：</b>\n{preview_text}\n\n"
                f"⚠️ <b>提示</b>：雲端儲存額度已滿，改以「文字摘要」回傳。"
            )
            Notifier.send_text(chat_id, report_msg, html=True)
    else:
        print(f"❌ 研究失敗: {result}")
        Notifier.send_text(chat_id, f"❌ 深度研究失敗: {result}", html=True)

if __name__ == "__main__":
    asyncio.run(main())
