import os
import sys
import json
import re
import base64
import subprocess
import uuid
import time
from datetime import datetime, timezone

def run_nlm(*args, env=None):
    # 強制使用統一的配置路徑
    current_env = os.environ.copy()
    home = os.path.expanduser("~")
    config_dir = os.path.join(home, ".notebooklm-mcp-cli")
    current_env["NLM_CONFIG_DIR"] = config_dir
    if env: current_env.update(env)
    
    cmd = ["nlm", *args]
    print(f"[CMD] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=current_env)
    if result.stdout: print(f"[STDOUT] {result.stdout.strip()}")
    if result.stderr: print(f"[STDERR] {result.stderr.strip()}")
    return result

def main():
    print("="*50)
    print(f"🚀 LazyTube-Assistant [VERSION: 2026.03.06.36 - FINAL DEBUG]")
    print("="*50)

    cookie_b64_raw = os.environ.get("NLM_COOKIE_BASE64", "")
    if cookie_b64_raw:
        print("--- [ 正在執行全系統路徑偵測與匯入 ] ---")
        try:
            cookie_data = base64.b64decode("".join(cookie_b64_raw.split()))
            temp_auth = os.path.abspath("temp_auth.json")
            with open(temp_auth, "wb") as f:
                f.write(cookie_data)

            # 1. 嘗試使用正確的子指令建立 Profile
            print("🔄 嘗試使用 nlm login profile create 指令...")
            run_nlm("login", "profile", "create", "default", "--auth-file", temp_auth, "--force")
            
            # 2. 如果失敗，嘗試標準匯入
            print("🔄 嘗試使用 nlm login --manual 指令...")
            run_nlm("login", "--manual", "--file", temp_auth, "--profile", "default", "--force")

            # 3. 深度搜尋：找出 profiles.json 到底在哪裡
            home = os.path.expanduser("~")
            print(f"🔍 正在搜尋 {home} 下的所有 profiles.json...")
            search = subprocess.run(["find", home, "-name", "profiles.json"], capture_output=True, text=True)
            found_paths = search.stdout.splitlines()
            
            if found_paths:
                for p in found_paths:
                    root_dir = os.path.dirname(p)
                    print(f"📍 發現配置目錄: {root_dir}")
                    # 讀取內容
                    with open(p, "r") as f: print(f"  📄 profiles.json 內容: {f.read()}")
                    # 暴力覆蓋該目錄下的所有可能憑證位置
                    p_default = os.path.join(root_dir, "profiles", "default")
                    os.makedirs(p_default, exist_ok=True)
                    for fname in ["auth.json", "default", "cookies.json"]:
                        with open(os.path.join(p_default, fname), "wb") as f: f.write(cookie_data)
                    print(f"  ✅ 已暴力覆蓋至 {p_default}")
            else:
                print("❌ 全系統搜尋不到 profiles.json！")

            if os.path.exists(temp_auth): os.remove(temp_auth)
            
            print("--- [ NLM 最終診斷 ] ---")
            run_nlm("doctor")
            print("="*50)
        except Exception as e:
            print(f"❌ 執行失敗: {e}")

    # --- [ 測試摘要 ] ---
    print("🧪 啟動測試摘要流程...")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    nb_name = f"FinalTest_{uuid.uuid4().hex[:4].upper()}"
    
    res = run_nlm("notebook", "create", nb_name)
    if res.returncode == 0:
        run_nlm("source", "add", nb_name, "--url", test_url)
        run_nlm("query", nb_name, "總結這部影片", "--confirm")
        run_nlm("notebook", "delete", nb_name, "--confirm")
    
    print("本次測試處理完成。")

if __name__ == "__main__":
    main()
