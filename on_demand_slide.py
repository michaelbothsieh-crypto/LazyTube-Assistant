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
    prompt = os.environ.get("INPUT_PROMPT") or ""
    slide_format = "pdf"
    slide_lang = "zh-TW"
    artifact_type = "slide_deck"

    # 解析嵌入在 Prompt 中的元數據 (格式: __META:lang,format,type__Prompt)
    if prompt.startswith("__META:"):
        import re
        # 支援 2 或 3 個參數的元數據
        match = re.match(r"^__META:([^,]+),([^,^__]+)(?:,([^__]+))?__", prompt)
        if match:
            slide_lang = match.group(1)
            slide_format = match.group(2)
            if match.group(3):
                artifact_type = match.group(3)
            # 找到第一個 __ 之後的內容
            prompt = prompt[prompt.find("__", 7) + 2:]
    
    print(f"--- 🚀 隨選內容生成任務啟動: {url} ---")
    print(f"📝 Prompt: {prompt}")
    print(f"📄 Type: {artifact_type}")
    print(f"📄 Format/Ext: {slide_format}")
    print(f"🌐 Lang: {slide_lang}")

    # 1. 認證環境佈署
    if not AuthManager.deploy_credentials():
        sys.exit(1)

    # 2. 處理影片並生成內容
    nlm = NotebookService()

    # 調用新的通用的處理方法
    file_path = nlm.process_artifact(
        url, 
        "On-Demand Content", 
        artifact_type=artifact_type,
        custom_prompt=prompt, 
        slide_format=slide_format, 
        slide_lang=slide_lang,
        language=slide_lang, # 給 infographic/report 用
        orientation="portrait", # 下面這兩個是圖片預設
        detail="detailed"
    )

    if file_path and os.path.exists(file_path):
        # 3. 通知 (傳送檔案)
        print(f"📡 正在發送內容至 {chat_id}...")
        
        type_name = {
            "slide_deck": "📊 簡報",
            "infographic": "🖼️ 圖片總結",
            "report": "📝 完整報告"
        }.get(artifact_type, "📄 內容檔案")

        caption = f"{type_name}已生成！\n🔗 來源：{url}"
        
        # 若是圖片則使用 send_photo (假設 Notifier 支援，否則沿用 send_document)
        if artifact_type == "infographic":
            success = Notifier.send_photo(target_chat_id=chat_id, file_path=file_path, caption=caption)
        else:
            success = Notifier.send_document(target_chat_id=chat_id, file_path=file_path, caption=caption)
        
        if success:
            print("✅ 發送成功")
        else:
            print("❌ 發送失敗 (Notifier 回報失敗)")
    else:
        print(f"❌ {artifact_type} 生成流程失敗，未取得檔案")

    # 4. 刪除處理中訊息 (僅限 Telegram) - 移出 else 區塊並確保在 exit 前執行
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

    if not (file_path and os.path.exists(file_path)):
        sys.exit(1)

if __name__ == "__main__":
    main()
