import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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

    # 1. 檢查是否為 Shorts
    from app.youtube import YouTubeService
    yt = YouTubeService()
    
    # 提取 Video ID
    video_id = None
    if "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]
    elif "youtube.com/watch" in url:
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        video_id = params.get("v", [None])[0]
    elif "youtube.com/shorts/" in url:
        video_id = url.split("youtube.com/shorts/")[1].split("?")[0]

    if video_id:
        details = yt._fetch_video_details([video_id])
        duration = details["durations"].get(video_id, 0)
        title = details["titles"].get(video_id, "").lower()
        if duration <= Config.SHORTS_MAX_SECONDS or "#shorts" in title:
            print(f"⚠️ 略過任務：偵測到影片為 Shorts ({duration}s)，依據設定不執行。")
            Notifier.send_error(chat_id, f"系統已設定過濾 Shorts 短片 (長度 {duration} 秒)，故不執行此任務。", url=url)
            Notifier.delete_pending_message(chat_id, message_id)
            return

    nlm = NotebookService()
    summary = nlm.process_video(url, "On-Demand Query", custom_prompt=prompt)

    if summary:
        if summary.startswith("❌"):
            print(f"❌ 偵測到執行錯誤: {summary}")
            Notifier.send_error(chat_id, summary.replace("❌", "").strip(), url=url)
        else:
            print(f"📡 正在發送通知至 {chat_id}...")
            success = Notifier.send_summary("隨選摘要結果", url, "手動觸發", summary, target_chat_id=chat_id)
            if success:
                print("✅ 通知發送成功")
    else:
        print("❌ 摘要生成失敗 (回傳 None)，發送預設錯誤通知...")
        Notifier.send_error(chat_id, "摘要生成失敗，請稍後再試或確認影片連結是否有效。", url=url)

    Notifier.delete_pending_message(chat_id, message_id)


if __name__ == "__main__":
    main()
