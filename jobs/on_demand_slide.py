import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import sys
import os
import re
from app.auth import AuthManager
from app.config import Config
from app.notebook import NotebookService
from app.notifier import Notifier


def main():
    if len(sys.argv) < 3:
        print("Usage: python on_demand_slide.py <url> <chat_id>")
        sys.exit(1)

    url = sys.argv[1]
    chat_id = sys.argv[2]
    message_id = os.environ.get("INPUT_MSG_ID")
    prompt = os.environ.get("INPUT_PROMPT") or ""
    slide_format = "pdf"
    slide_lang = "zh-TW"
    artifact_type = "slide_deck"

    # 解析嵌入在 Prompt 中的元數據 (格式: __META:lang,format,type__Prompt)
    if prompt.startswith("__META:"):
        match = re.match(r"^__META:([^,]+),([^,^__]+)(?:,([^__]+))?__", prompt)
        if match:
            slide_lang = match.group(1)
            slide_format = match.group(2)
            if match.group(3):
                artifact_type = match.group(3)
            prompt = prompt[prompt.find("__", 7) + 2:]

    print(f"--- 🚀 隨選內容生成任務啟動: {url} ---")
    print(f"📝 Prompt: {prompt}")
    print(f"📄 Type: {artifact_type}")
    print(f"📄 Format/Ext: {slide_format}")
    print(f"🌐 Lang: {slide_lang}")

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
        if duration <= Config.SHORTS_MAX_SECONDS:
            print(f"⚠️ 略過任務：偵測到影片為 Shorts ({duration}s)，依據設定不執行。")
            Notifier.send_error(chat_id, f"系統已設定過濾 Shorts 短片 (長度 {duration} 秒)，故不執行此任務。", url=url)
            Notifier.delete_pending_message(chat_id, message_id)
            return

    nlm = NotebookService()

    file_path = nlm.process_artifact(
        url,
        "On-Demand Content",
        artifact_type=artifact_type,
        custom_prompt=prompt,
        slide_format=slide_format,
        slide_lang=slide_lang,
        language=slide_lang,
        orientation="portrait",
        detail="detailed"
    )

    if file_path and not file_path.startswith("❌") and os.path.exists(file_path):
        print(f"📡 正在發送內容至 {chat_id}...")

        type_name = {
            "slide_deck": "📊 簡報",
            "infographic": "🖼️ 圖片總結",
            "report": "📝 完整報告"
        }.get(artifact_type, "📄 內容檔案")

        caption = f"{type_name}已生成！\n🔗 來源：{url}"

        if artifact_type == "infographic":
            success = Notifier.send_photo(target_chat_id=chat_id, file_path=file_path, caption=caption)
        else:
            success = Notifier.send_document(target_chat_id=chat_id, file_path=file_path, caption=caption)

        if success:
            print("✅ 發送成功")
        else:
            print("❌ 發送失敗 (Notifier 回報失敗)")
    else:
        error_msg = file_path if file_path and file_path.startswith("❌") else f"❌ {artifact_type} 生成失敗，請稍後再試或確認影片連結是否有效。"
        print(f"❌ 流程失敗: {error_msg}")
        Notifier.send_error(chat_id, error_msg.replace("❌", "").strip(), url=url)

    Notifier.delete_pending_message(chat_id, message_id)

    if not (file_path and os.path.exists(file_path)):
        sys.exit(1)


if __name__ == "__main__":
    main()
