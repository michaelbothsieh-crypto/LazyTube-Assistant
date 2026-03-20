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

        # 在 GitHub Actions 日誌中遮罩憑證
        print(f"::add-mask::{Config.NLM_COOKIE_BASE64}")

        try:
            full_data_bytes = base64.b64decode("".join(Config.NLM_COOKIE_BASE64.split()))
            full_json = json.loads(full_data_bytes)
            
            home = os.path.expanduser("~")
            # 關鍵：還原到昨天的路徑 ~/.notebooklm-mcp-cli
            config_dir = os.path.join(home, ".notebooklm-mcp-cli")
            profile_dir = os.path.join(config_dir, "profiles", "default")
            os.makedirs(profile_dir, exist_ok=True)
            
            # 佈署核心檔案
            with open(os.path.join(profile_dir, "auth.json"), "wb") as f: f.write(full_data_bytes)
            with open(os.path.join(profile_dir, "cookies.json"), "w") as f: json.dump(full_json.get("cookies", []), f)
            with open(os.path.join(profile_dir, "metadata.json"), "w") as f: 
                json.dump({k: v for k, v in full_json.items() if k != "cookies"}, f)
            with open(os.path.join(config_dir, "profiles.json"), "w") as f:
                json.dump({"default_profile": "default", "profiles": {"default": {}}}, f)
            
            return True
        except Exception as e:
            print(f"❌ 憑證佈署失敗: {e}")
            return False
