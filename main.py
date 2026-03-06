import os
import sys
import json
import re
import base64
import subprocess
import uuid
import time
from datetime import datetime, timezone

def run_nlm(*args):
    home = os.path.expanduser("~")
    config_dir = os.path.join(home, ".notebooklm-mcp-cli")
    env = os.environ.copy()
    env["NLM_CONFIG_DIR"] = config_dir
    
    cmd = ["nlm", *args]
    print(f"[CMD] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.stdout: print(f"[STDOUT] {result.stdout.strip()}")
    if result.stderr: print(f"[STDERR] {result.stderr.strip()}")
    return result

def main():
    print("="*50)
    print(f"🚀 LazyTube-Assistant [VERSION: 2026.03.06.38 - PRECISE INJECTION]")
    print("="*50)

    cookie_b64_raw = os.environ.get("NLM_COOKIE_BASE64", "")
    if cookie_b64_raw:
        print("--- [ 正在執行精確數據解構與注入 ] ---")
        try:
            full_data_bytes = base64.b64decode("".join(cookie_b64_raw.split()))
            full_json = json.loads(full_data_bytes)
            
            # 1. 準備三種不同格式的數據
            pure_cookies = full_json.get("cookies", [])
            metadata_only = {k: v for k, v in full_json.items() if k != "cookies"}
            
            # 2. 讓官方指令初始化目錄
            temp_cookies_path = os.path.abspath("temp_cookies.json")
            with open(temp_cookies_path, "w") as f:
                json.dump(pure_cookies, f)
            
            print("🔄 步驟 A: 執行目錄結構初始化...")
            run_nlm("login", "--manual", "--file", temp_cookies_path, "--profile", "default", "--force")
            
            # 3. 步驟 B: 精確調包 (將正確的數據放入正確的檔案)
            home = os.path.expanduser("~")
            profile_dir = os.path.join(home, ".notebooklm-mcp-cli", "profiles", "default")
            
            if os.path.exists(profile_dir):
                # auth.json -> 完整數據
                with open(os.path.join(profile_dir, "auth.json"), "wb") as f:
                    f.write(full_data_bytes)
                
                # cookies.json -> 僅列表 (List)
                with open(os.path.join(profile_dir, "cookies.json"), "w") as f:
                    json.dump(pure_cookies, f)
                
                # metadata.json -> 僅元數據 (Dict)
                with open(os.path.join(profile_dir, "metadata.json"), "w") as f:
                    json.dump(metadata_only, f)
                
                print(f"✅ 步驟 B: 已完成精確數據注入至 {profile_dir}")
            
            if os.path.exists(temp_cookies_path): os.remove(temp_cookies_path)
            
            print("--- [ NLM 認證診斷 ] ---")
            run_nlm("doctor")
            print("="*50)
        except Exception as e:
            print(f"❌ 佈署失敗: {e}")

    # --- [ 測試摘要 ] ---
    print("🧪 啟動測試摘要流程...")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    nb_name = f"Test_{uuid.uuid4().hex[:4].upper()}"
    
    res = run_nlm("notebook", "create", nb_name)
    if res.returncode == 0:
        run_nlm("source", "add", nb_name, "--url", test_url)
        run_nlm("query", nb_name, "請用繁體中文總結", "--confirm")
        run_nlm("notebook", "delete", nb_name, "--confirm")
    
    print("本次測試處理完成。")

if __name__ == "__main__":
    main()
