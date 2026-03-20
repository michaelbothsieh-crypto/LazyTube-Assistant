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
            
            # 1. 確保 Cookie 格式正確 (String 格式)
            cookies_raw = full_json.get("cookies", [])
            if isinstance(cookies_raw, list):
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies_raw if 'name' in c and 'value' in c])
                full_json["cookies"] = cookie_str
            
            home = os.path.expanduser("~")
            config_dir = os.path.normpath(os.path.join(home, ".config", "notebooklm-mcp-cli"))
            profile_dir = os.path.join(config_dir, "profiles", "default")
            os.makedirs(profile_dir, exist_ok=True)
            
            # 2. 佈署 auth.json 到兩個可能的位置 (根目錄與 Profile 目錄)
            with open(os.path.join(profile_dir, "auth.json"), "w", encoding="utf-8") as f:
                json.dump(full_json, f)
            with open(os.path.join(config_dir, "auth.json"), "w", encoding="utf-8") as f:
                json.dump(full_json, f)
            
            # 3. 建立極致相容的 profiles.json
            # 包含所有已知版本的欄位：active_profile, default_profile, 及其詳細路徑
            profile_config = {
                "active_profile": "default",
                "default_profile": "default",
                "profiles": {
                    "default": {
                        "name": "default",
                        "path": profile_dir,
                        "auth_path": os.path.join(profile_dir, "auth.json")
                    }
                }
            }
            with open(os.path.join(config_dir, "profiles.json"), "w", encoding="utf-8") as f:
                json.dump(profile_config, f)
            
            # 4. 舊路徑同步備援
            old_config_dir = os.path.join(home, ".notebooklm-mcp-cli")
            old_profile_dir = os.path.join(old_config_dir, "profiles", "default")
            os.makedirs(old_profile_dir, exist_ok=True)
            with open(os.path.join(old_profile_dir, "auth.json"), "w", encoding="utf-8") as f:
                json.dump(full_json, f)
            with open(os.path.join(old_config_dir, "profiles.json"), "w", encoding="utf-8") as f:
                json.dump(profile_config, f)

            print(f"✅ 憑證已完成全方位備援佈署")
            return True
        except Exception as e:
            print(f"❌ 憑證佈署異常: {e}")
            return False
