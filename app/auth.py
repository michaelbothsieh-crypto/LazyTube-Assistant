import os
import json
import base64
import subprocess
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
            print("⚠️ 找不到 NLM_COOKIE_BASE64，略過憑證佈署")
            return False

        try:
            full_data_bytes = base64.b64decode("".join(Config.NLM_COOKIE_BASE64.split()))
            full_json = json.loads(full_data_bytes)
            
            home = os.path.expanduser("~")
            config_dir = os.path.join(home, ".notebooklm-mcp-cli")
            profile_dir = os.path.join(config_dir, "profiles", "default")
            os.makedirs(profile_dir, exist_ok=True)
            
            # 1. 完整認證 JSON
            with open(os.path.join(profile_dir, "auth.json"), "wb") as f:
                f.write(full_data_bytes)
            
            # 2. 核心 Cookie 列表 (List)
            with open(os.path.join(profile_dir, "cookies.json"), "w") as f:
                json.dump(full_json.get("cookies", []), f)
            
            # 3. 核心元數據 (Dict)
            metadata = {k: v for k, v in full_json.items() if k != "cookies"}
            with open(os.path.join(profile_dir, "metadata.json"), "w") as f:
                json.dump(metadata, f)
            
            # 4. Profile 宣告
            with open(os.path.join(config_dir, "profiles.json"), "w") as f:
                json.dump({"default_profile": "default", "profiles": {"default": {}}}, f)
            
            print(f"✅ 憑證環境已成功佈署至: {profile_dir}")
            return True
        except Exception as e:
            print(f"❌ 憑證佈署失敗: {e}")
            return False
