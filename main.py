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
    # 強制指定配置路徑
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
    print(f"🚀 LazyTube-Assistant [VERSION: 2026.03.06.37 - THE FINAL BAIT]")
    print("="*50)

    cookie_b64_raw = os.environ.get("NLM_COOKIE_BASE64", "")
    if cookie_b64_raw:
        print("--- [ 正在執行智能拆解與調包佈署 ] ---")
        try:
            full_data = base64.b64decode("".join(cookie_b64_raw.split()))
            full_json = json.loads(full_data)
            
            # 1. 拆解出純 Cookie (指令只認這個)
            pure_cookies = full_json.get("cookies", full_json)
            temp_cookies_path = os.path.abspath("temp_cookies.json")
            with open(temp_cookies_path, "w") as f:
                json.dump(pure_cookies, f)
            
            # 2. 讓官方指令初始化 (這會成功建立 profiles/default 目錄)
            print("🔄 步驟 A: 使用純 Cookie 匯入以初始化目錄結構...")
            run_nlm("login", "--manual", "--file", temp_cookies_path, "--profile", "default", "--force")
            
            # 3. 立即調包：用完整的合併數據覆蓋掉所有檔案
            home = os.path.expanduser("~")
            base_dir = os.path.join(home, ".notebooklm-mcp-cli")
            profile_dir = os.path.join(base_dir, "profiles", "default")
            
            # 覆蓋所有可能的憑證檔名
            if os.path.exists(profile_dir):
                for fname in ["auth.json", "cookies.json", "metadata.json", "default"]:
                    fpath = os.path.join(profile_dir, fname)
                    with open(fpath, "wb") as f:
                        f.write(full_data)
                print(f"✅ 步驟 B: 已成功調包，將完整憑證注入至 {profile_dir}")
            else:
                # 備案：如果目錄沒建成功，我們強行手動建
                os.makedirs(profile_dir, exist_ok=True)
                with open(os.path.join(profile_dir, "auth.json"), "wb") as f:
                    f.write(full_data)
                with open(os.path.join(base_dir, "profiles.json"), "w") as f:
                    json.dump({"default_profile": "default", "profiles": {"default": {"auth_file": "auth.json"}}}, f)
                print(f"✅ 步驟 B (備案): 已手動建立並注入完整憑證。")

            if os.path.exists(temp_cookies_path): os.remove(temp_cookies_path)
            
            print("--- [ NLM 認證診斷 ] ---")
            run_nlm("doctor")
            print("="*50)
        except Exception as e:
            print(f"❌ 佈署失敗: {e}")

    # --- [ 測試摘要 ] ---
    print("🧪 啟動測試摘要流程...")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    nb_name = f"Final_{uuid.uuid4().hex[:4].upper()}"
    
    res = run_nlm("notebook", "create", nb_name)
    if res.returncode == 0:
        run_nlm("source", "add", nb_name, "--url", test_url)
        run_nlm("query", nb_name, "這影片說什麼", "--confirm")
        run_nlm("notebook", "delete", nb_name, "--confirm")
    
    print("本次測試處理完成。")

if __name__ == "__main__":
    main()
