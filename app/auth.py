import os
import json
import base64
from app.config import Config

class AuthManager:
    """
    /// NotebookLM 憑證管理模組
    /// 負責還原 GitHub Actions 環境下的認證環境
    """

    @staticmethod
    def deploy_credentials():
        """
        /// 將 NLM_COOKIE_BASE64 解碼並佈署到 CLI 預期路徑
        /// 遵循 GEMINI.md 規範：佈署至 ~/.config/notebooklm-mcp-cli
        """
        if not Config.NLM_COOKIE_BASE64:
            return False

        print(f"::add-mask::{Config.NLM_COOKIE_BASE64}")

        try:
            # 1. 解碼並解析原始資料
            full_data_bytes = base64.b64decode("".join(Config.NLM_COOKIE_BASE64.split()))
            full_json = json.loads(full_data_bytes)
            
            # 2. 核心修正：將 Cookie 列表轉換為字串 (v0.4.6+ 強制要求)
            # 這是解決 400 Bad Request 的關鍵
            cookies_raw = full_json.get("cookies", [])
            if isinstance(cookies_raw, list):
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies_raw if 'name' in c and 'value' in c])
                full_json["cookies"] = cookie_str
                print(f"🍪 已將 {len(cookies_raw)} 個 Cookie 轉換為字串格式")
            
            home = os.expanduser("~")
            config_dir = os.path.join(home, ".config", "notebooklm-mcp-cli")
            profile_dir = os.path.join(config_dir, "profiles", "default")
            os.makedirs(profile_dir, exist_ok=True)
            
            # 3. 佈署 auth.json (確保內容是轉換後的 JSON)
            with open(os.path.join(profile_dir, "auth.json"), "w", encoding="utf-8") as f: 
                json.dump(full_json, f)
            
            # 4. 同步佈署原始檔案以增加相容性
            metadata = {k: v for k, v in full_json.items() if k != "cookies"}
            with open(os.path.join(profile_dir, "metadata.json"), "w", encoding="utf-8") as f:
                json.dump(metadata, f)
            with open(os.path.join(profile_dir, "cookies.json"), "w", encoding="utf-8") as f:
                # 這裡保留原始列表格式以防萬一
                json.dump(cookies_raw, f)
            
            # 5. 佈署 profiles.json (宣告格式)
            profile_config = {
                "active_profile": "default",
                "default_profile": "default",
                "profiles": {
                    "default": {
                        "name": "default"
                    }
                }
            }
            with open(os.path.join(config_dir, "profiles.json"), "w", encoding="utf-8") as f:
                json.dump(profile_config, f)

            print(f"✅ 憑證已更新 Cookie 格式並佈署至 {config_dir}")
            return True
        except Exception as e:
            print(f"❌ 憑證佈署異常: {e}")
            return False
