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
        print("🎨 正在生成專業報告...")
        html_content = Notifier.generate_html_report(topic, result)
        
        is_line = str(chat_id).startswith(("U", "C", "R"))
        
        # 提取摘要預覽
        preview_text = result[:400] + "..." if len(result) > 400 else result
        report_msg = f"🔎 <b>深度研究完成：{topic}</b>\n\n📝 <b>核心摘要預覽：</b>\n{preview_text}"
        
        if is_line:
            # LINE 流程：生成 PDF -> 存入 Redis -> 發送代理連結
            print("📄 正在為 LINE 用戶生成 PDF 報告...")
            pdf_path = Notifier.generate_pdf_report(html_content)
            if pdf_path:
                Notifier.send_document(chat_id, pdf_path, caption=report_msg)
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            else:
                Notifier.send_text(chat_id, report_msg + "\n\n⚠️ PDF 生成失敗，請參考上方摘要。", html=True)
        else:
            # TG 流程：直接傳送 HTML 文件
            import uuid
            html_path = f"/tmp/report_{uuid.uuid4().hex[:8]}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            Notifier.send_document(chat_id, html_path, caption=report_msg)
            if os.path.exists(html_path):
                os.remove(html_path)
        
        print("✅ 研究完成並已回傳")
    else:
        print(f"❌ 研究失敗: {result}")
        Notifier.send_text(chat_id, f"❌ 深度研究失敗: {result}", html=True)

if __name__ == "__main__":
    asyncio.run(main())
