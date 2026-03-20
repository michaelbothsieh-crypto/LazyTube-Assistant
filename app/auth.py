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
        /// 加入 GitHub Actions ::add-mask:: 指令以保護隱私
        """
        if not Config.NLM_COOKIE_BASE64:
            return False

        # 在 GitHub Actions 日誌中遮罩憑證
        print(f"::add-mask::{Config.NLM_COOKIE_BASE64}")

        try:
            full_data_bytes = base64.b64decode("".join(Config.NLM_COOKIE_BASE64.split()))
            
            home = os.path.expanduser("~")
            # 根據系統記憶對齊路徑
            config_dir = os.path.join(home, ".config", "notebooklm-mcp-cli")
            profile_dir = os.path.join(config_dir, "profiles", "default")
            os.makedirs(profile_dir, exist_ok=True)
            
            # 佈署核心檔案：auth.json 在 v0.4.0+ 是合併了 metadata 與 cookies 的 JSON
            auth_path = os.path.join(profile_dir, "auth.json")
            with open(auth_path, "wb") as f: 
                f.write(full_data_bytes)
            
            # 建立 profiles.json 導向至 default，並明確宣告 default profile
            # 使用雙重欄位宣告以相容新舊版本 (v0.4.0 ~ v0.4.6)
            profile_config = {
                "active_profile": "default",
                "default_profile": "default",
                "profiles": {
                    "default": {"name": "default"}
                }
            }
            with open(os.path.join(config_dir, "profiles.json"), "w") as f:
                json.dump(profile_config, f)
            
            # 偵錯：印出佈署後的路徑結構
            print(f"📂 設定目錄結構診斷:")
            for root, dirs, files in os.walk(config_dir):
                level = root.replace(config_dir, '').count(os.sep)
                indent = ' ' * 4 * level
                print(f"{indent}{os.path.basename(root)}/")
                sub_indent = ' ' * 4 * (level + 1)
                for f in files:
                    print(f"{sub_indent}{f}")

            print(f"✅ 憑證已佈署至 {config_dir}")
            return True
        except Exception as e:
            print(f"❌ 憑證佈署失敗: {e}")
            return False
