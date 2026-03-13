import sys
import os
from app.auth import AuthManager
from app.config import Config
from app.notebook import NotebookService
from app.notifier import Notifier


def main():
    if len(sys.argv) < 3:
        print("Usage: python on_demand.py <url> <chat_id> [prompt]")
        sys.exit(1)

    url = sys.argv[1]
    chat_id = sys.argv[2]
    prompt = sys.argv[3] if len(sys.argv) > 3 else "請用繁體中文列出 5 個核心重點，並加上影片標題。"
    message_id = os.environ.get("INPUT_MSG_ID")

    print(f"--- 🚀 隨選摘要任務啟動: {url} ---")

    Config.validate()

    if not AuthManager.deploy_credentials():
        sys.exit(1)

    nlm = NotebookService()
    summary = nlm.process_video(url, "On-Demand Query", custom_prompt=prompt)

    if summary:
        print(f"📡 正在發送通知至 {chat_id}...")
        success = Notifier.send_summary("隨選摘要結果", url, "手動觸發", summary, target_chat_id=chat_id)
        if success:
            print("✅ 通知發送成功")
    else:
        print("❌ 摘要生成失敗，發送錯誤通知...")
        Notifier.send_error(chat_id, "摘要生成失敗，請稍後再試或確認影片連結是否有效。", url=url)

    Notifier.delete_pending_message(chat_id, message_id)


if __name__ == "__main__":
    main()
