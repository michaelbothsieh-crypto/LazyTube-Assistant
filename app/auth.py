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
            
            home = os.path.expanduser("~")
            # 根據 Added Memories，目標路徑為 ~/.config/notebooklm-mcp-cli
            config_dir = os.path.join(home, ".config", "notebooklm-mcp-cli")
            profile_dir = os.path.join(config_dir, "profiles", "default")
            os.makedirs(profile_dir, exist_ok=True)
            
            # 2. 佈署 auth.json (合併體)
            with open(os.path.join(profile_dir, "auth.json"), "wb") as f: 
                f.write(full_data_bytes)
            
            # 3. 佈署 metadata.json 與 cookies.json (備援與相容性)
            metadata = {k: v for k, v in full_json.items() if k != "cookies"}
            cookies = full_json.get("cookies", [])
            with open(os.path.join(profile_dir, "metadata.json"), "w") as f:
                json.dump(metadata, f)
            with open(os.path.join(profile_dir, "cookies.json"), "w") as f:
                json.dump(cookies, f)
            
            # 4. 佈署 profiles.json (宣告格式對齊 v0.4.6+)
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

            print(f"✅ 憑證已嚴格遵循規範佈署至 {config_dir}")
            return True
        except Exception as e:
            print(f"❌ 憑證佈署異常: {e}")
            return False
