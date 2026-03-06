import os
import sys
import json
import re
import base64
import subprocess
import uuid
import time
from datetime import datetime, timezone

# 配置區域
LAST_CHECK_FILE = "last_check.txt"

def run_nlm(*args):
    cmd = ["nlm", *args]
    print(f"[CMD] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout: print(f"[STDOUT] {result.stdout.strip()}")
    if result.stderr: print(f"[STDERR] {result.stderr.strip()}")
    return result

def main():
    print("="*50)
    print(f"🚀 LazyTube-Assistant [VERSION: 2026.03.06.35 - DEBUG MODE]")
    print("="*50)

    # 1. 認證初始化與深度偵查
    cookie_b64_raw = os.environ.get("NLM_COOKIE_BASE64", "")
    if cookie_b64_raw:
        print("--- [ 正在執行認證調包 4.0 + 深度偵查 ] ---")
        try:
            cookie_data = base64.b64decode("".join(cookie_b64_raw.split()))
            temp_auth = os.path.abspath("temp_auth.json")
            with open(temp_auth, "wb") as f:
                f.write(cookie_data)

            # 步驟 A: 執行初始化
            subprocess.run(["nlm", "login", "--manual", "--file", temp_auth, "--profile", "default", "--force"], capture_output=True)
            
            home = os.path.expanduser("~")
            config_dir = os.path.join(home, ".notebooklm-mcp-cli")
            
            # 偵查：列出所有檔案
            print("📂 偵查目錄結構:")
            for root, dirs, files in os.walk(config_dir):
                for f in files:
                    print(f"  📄 {os.path.join(root, f)}")

            # 步驟 B: 多重覆蓋 (Shotgun Overwrite)
            targets = [
                os.path.join(config_dir, "profiles", "default", "auth.json"),
                os.path.join(config_dir, "profiles", "default", "config.json"),
                os.path.join(config_dir, "profiles", "default", "metadata.json"),
                os.path.join(config_dir, "auth.json")
            ]
            
            for t in targets:
                try:
                    os.makedirs(os.path.dirname(t), exist_ok=True)
                    with open(t, "wb") as f:
                        f.write(cookie_data)
                    print(f"✅ 已覆蓋: {t}")
                except Exception as e:
                    print(f"⚠️ 無法覆蓋 {t}: {e}")

            if os.path.exists(temp_auth): os.remove(temp_auth)
            
            print("--- [ NLM 認證診斷 ] ---")
            run_nlm("doctor")
            print("="*50)
        except Exception as e:
            print(f"❌ 偵查失敗: {e}")

    # --- [ 測試模式：Rickroll ] ---
    print("🧪 測試摘要執行中...")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    notebook_name = f"Test_{uuid.uuid4().hex[:4].upper()}"
    
    # 執行建立
    res = run_nlm("notebook", "create", notebook_name)
    if res.returncode == 0:
        run_nlm("source", "add", notebook_name, "--url", test_url)
        # 嘗試查詢
        run_nlm("query", notebook_name, "請用繁體中文總結", "--confirm")
        # 清理
        run_nlm("notebook", "delete", notebook_name, "--confirm")
    
    print("本次測試處理完成。")

if __name__ == "__main__":
    main()
