import json
import base64
import os
import sys

def main():
    print("--- 🤖 LazyTube Auth Tool ---")
    print("本工具將合併 cookies.json 與 metadata.json 並產出 GitHub 所需的 Base64 字串。\n")
    
    cookies_file = "cookies.json"
    metadata_file = "metadata.json"
    
    if not os.path.exists(cookies_file) or not os.path.exists(metadata_file):
        print("❌ 錯誤：請確保目錄下有 cookies.json 與 metadata.json 檔案。")
        print("提示：這些檔案通常在 ~/.notebooklm-mcp-cli/profiles/default/ 目錄下。")
        sys.exit(1)
        
    try:
        with open(cookies_file, 'r') as f: cookies = json.load(f)
        with open(metadata_file, 'r') as f: meta = json.load(f)
        
        meta['cookies'] = cookies
        combined = json.dumps(meta)
        b64_output = base64.b64encode(combined.encode()).decode()
        
        print("✅ 合併成功！以下是您的 NLM_COOKIE_BASE64 (已自動刪除換行)：\n")
        print("-" * 50)
        print(b64_output)
        print("-" * 50)
        print("\n🚀 請複製上方所有內容並貼到 GitHub Secret。")
        
    except Exception as e:
        print(f"❌ 處理過程中發生錯誤: {e}")

if __name__ == "__main__":
    main()
