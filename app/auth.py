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
        """
        if not Config.NLM_COOKIE_BASE64:
            print("❌ 找不到 NLM_COOKIE_BASE64 環境變數")
            return False

        print(f"::add-mask::{Config.NLM_COOKIE_BASE64}")

        try:
            # 1. 解碼並解析 JSON
            full_data_bytes = base64.b64decode("".join(Config.NLM_COOKIE_BASE64.split()))
            full_json = json.loads(full_data_bytes)
            
            # 2. 核心修正：確保 Cookie 是字串格式 (v0.4.6+ 必須)
            cookies_raw = full_json.get("cookies", [])
            if isinstance(cookies_raw, list):
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies_raw if 'name' in c and 'value' in c])
                full_json["cookies"] = cookie_str
                print("🍪 已將 Cookie JSON 列表轉換為標準字串格式")
            
            # 3. 準備路徑 (對齊最新標準)
            home = os.path.expanduser("~")
            config_dir = os.path.join(home, ".config", "notebooklm-mcp-cli")
            profile_dir = os.path.join(config_dir, "profiles", "default")
            os.makedirs(profile_dir, exist_ok=True)
            
            # 4. 寫入 auth.json (合併 metadata 與 cookies)
            with open(os.path.join(profile_dir, "auth.json"), "w", encoding="utf-8") as f: 
                json.dump(full_json, f)
            
            # 5. 寫入 profiles.json (最精簡格式)
            profile_config = {
                "active_profile": "default",
                "profiles": {
                    "default": {
                        "name": "default"
                    }
                }
            }
            with open(os.path.join(config_dir, "profiles.json"), "w", encoding="utf-8") as f:
                json.dump(profile_config, f)

            print(f"✅ 憑證已成功佈署至 {config_dir}")
            return True
        except Exception as e:
            print(f"❌ 憑證佈署過程發生異常: {e}")
            return False
