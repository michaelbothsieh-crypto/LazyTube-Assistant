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

def process_with_notebooklm(video_url, title):
    print(f"正在處理: {title} ({video_url})")
    notebook_name = f"YT_{uuid.uuid4().hex[:4].upper()}"
    notebook_id = None
    summary_text = None
    
    try:
        # 1. 建立筆記本
        res = run_nlm("notebook", "create", notebook_name)
        if res.returncode == 0:
            match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
            notebook_id = match.group(1) if match else notebook_name
            print(f"📌 使用 Notebook ID: {notebook_id}")
        else: return None
        
        # 2. 新增來源
        res = run_nlm("source", "add", notebook_id, "--url", video_url)
        
        if res.returncode == 0:
            # 3. 執行查詢 (嘗試 0.4.0 正確語法)
            query = "請用繁體中文列出這部影片的 3 到 5 個核心重點，並加上影片標題"
            
            # 嘗試語法 A: nlm query notebook <ID> <Prompt>
            print("🔄 嘗試語法 A: nlm query notebook...")
            res = run_nlm("query", "notebook", notebook_id, query)
            
            # 嘗試語法 B: nlm describe notebook <ID> (如果 A 失敗)
            if res.returncode != 0:
                print("🔄 嘗試語法 B: nlm describe notebook...")
                res = run_nlm("describe", "notebook", notebook_id)
            
            if res.returncode == 0:
                summary_text = res.stdout.strip()
    finally:
        if notebook_id:
            run_nlm("notebook", "delete", notebook_id, "--confirm")
    return summary_text

def main():
    print("="*50)
    print(f"🚀 LazyTube-Assistant [VERSION: 2026.03.06.41 - AUTO-FIXED]")
    print("="*50)

    # 1. 認證佈署
    cookie_b64_raw = os.environ.get("NLM_COOKIE_BASE64", "")
    if cookie_b64_raw:
        try:
            full_data_bytes = base64.b64decode("".join(cookie_b64_raw.split()))
            full_json = json.loads(full_data_bytes)
            home = os.path.expanduser("~")
            profile_dir = os.path.join(home, ".notebooklm-mcp-cli", "profiles", "default")
            os.makedirs(profile_dir, exist_ok=True)
            
            with open(os.path.join(profile_dir, "auth.json"), "wb") as f: f.write(full_data_bytes)
            with open(os.path.join(profile_dir, "cookies.json"), "w") as f: json.dump(full_json.get("cookies", []), f)
            with open(os.path.join(profile_dir, "metadata.json"), "w") as f: json.dump({k:v for k,v in full_json.items() if k!="cookies"}, f)
            with open(os.path.join(os.path.dirname(profile_dir), "..", "profiles.json"), "w") as f:
                json.dump({"default_profile": "default", "profiles": {"default": {}}}, f)
            print("✅ 憑證環境佈署成功。")
        except Exception as e: print(f"❌ 佈署失敗: {e}")

    # 2. 測試摘要
    test_url = "https://www.youtube.com/watch?v=t5RVVWUS9nk"
    summary = process_with_notebooklm(test_url, "POEGuy Live Stream")
    
    if summary:
        print(f"\n🎉 摘要產出成功！\n{summary}")
    else:
        print("\n❌ 摘要產出失敗。")
    
    print("本次測試處理完成。")

if __name__ == "__main__":
    main()
