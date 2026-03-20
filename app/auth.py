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
            return False

        print(f"::add-mask::{Config.NLM_COOKIE_BASE64}")

        try:
            full_data_bytes = base64.b64decode("".join(Config.NLM_COOKIE_BASE64.split()))
            full_json = json.loads(full_data_bytes)
            
            # 確保 Cookie 格式正確 (String 格式)
            cookies_raw = full_json.get("cookies", [])
            if isinstance(cookies_raw, list):
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies_raw if 'name' in c and 'value' in c])
                full_json["cookies"] = cookie_str
            
            # 根據 v0.4.6 原始碼 (utils/config.py) 對齊路徑
            home = os.path.expanduser("~")
            config_dir = os.path.join(home, ".notebooklm-mcp-cli")
            profile_dir = os.path.join(config_dir, "profiles", "default")
            os.makedirs(profile_dir, exist_ok=True)
            
            # 佈署 auth.json (這是 v0.4.6 最關鍵的檔案)
            with open(os.path.join(profile_dir, "auth.json"), "w", encoding="utf-8") as f:
                json.dump(full_json, f)
            
            # 建立符合 v0.4.6 預期的 profiles.json
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

            print(f"✅ 憑證已成功佈署至 {config_dir} (v0.4.6 標準)")
            return True
        except Exception as e:
            print(f"❌ 憑證佈署異常: {e}")
            return False
