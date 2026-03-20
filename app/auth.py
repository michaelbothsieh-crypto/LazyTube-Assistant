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
            full_json = json.loads(full_data_bytes)
            
            # 關鍵修正：轉換 Cookie 格式 (從 JSON List 轉為 String)
            # 這是因為 nlm v0.4.0+ 的 auth.json 預期 cookies 是分號分隔的字串
            cookies_raw = full_json.get("cookies", [])
            if isinstance(cookies_raw, list):
                # 將 [{name: "...", value: "..."}, ...] 轉為 "name1=value1; name2=value2"
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies_raw if 'name' in c and 'value' in c])
                full_json["cookies"] = cookie_str
                print("🍪 已將 Cookie 從 JSON 列表轉換為字串格式")
            
            home = os.path.expanduser("~")
            config_dir = os.path.join(home, ".config", "notebooklm-mcp-cli")
            profile_dir = os.path.join(config_dir, "profiles", "default")
            os.makedirs(profile_dir, exist_ok=True)
            
            # 佈署核心檔案：auth.json
            with open(os.path.join(profile_dir, "auth.json"), "w") as f: 
                json.dump(full_json, f)
            
            # 建立 profiles.json 導向至 default
            profile_config = {
                "active_profile": "default",
                "profiles": {
                    "default": {
                        "name": "default"
                    }
                }
            }
            with open(os.path.join(config_dir, "profiles.json"), "w") as f:
                json.dump(profile_config, f)
            
            # 同時也同步一份到舊的路徑 ~/.notebooklm-mcp-cli 以防萬一
            old_config_dir = os.path.join(home, ".notebooklm-mcp-cli")
            old_profile_dir = os.path.join(old_config_dir, "profiles", "default")
            os.makedirs(old_profile_dir, exist_ok=True)
            with open(os.path.join(old_profile_dir, "auth.json"), "w") as f: json.dump(full_json, f)
            with open(os.path.join(old_config_dir, "profiles.json"), "w") as f:
                json.dump(profile_config, f)

            print(f"✅ 憑證已同步佈署至 XDG 與舊版路徑")
            return True
        except Exception as e:
            print(f"❌ 憑證佈署失敗: {e}")
            return False
