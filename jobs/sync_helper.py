"""
狀態同步小幫手 (Git 分支儲存版)
- 替代 Vercel Blob 以解決額度限制
- 使用 state 獨立分支存儲，不污染主分支歷史
"""
import os
import json
import sys
import subprocess
import urllib.request as r

# 配置
STATE_BRANCH = "state"
GH_OWNER = os.environ.get("GH_REPO_OWNER")
GH_REPO = os.environ.get("GH_REPO_NAME")
GH_PAT = os.environ.get("GH_PAT_WORKFLOW")

import base64
from itertools import cycle

# 配置
STATE_BRANCH = "state"
GH_OWNER = os.environ.get("GH_REPO_OWNER")
GH_REPO = os.environ.get("GH_REPO_NAME")
GH_PAT = os.environ.get("GH_PAT_WORKFLOW")
SECRET = os.environ.get("TG_WEBHOOK_SECRET", "default_key")

# 檔名對照表 (模糊化)
FILE_MAP = {
    "processed_videos.txt": ".sys_vid_cache",
    "last_check.txt": ".sys_time_sync",
    "subscriptions.json": ".sys_sub_conf"
}

def _crypt(data: bytes) -> bytes:
    """使用 XOR 進行簡單加密/解密"""
    return bytes([b ^ k for b, k in zip(data, cycle(SECRET.encode()))])

def dl_state():
    """從 GitHub 下載並解密狀態"""
    print(f"📡 正在從 {STATE_BRANCH} 分支還原加密狀態...")
    _init_empty_files()

    base_url = f"https://raw.githubusercontent.com/{GH_OWNER}/{GH_REPO}/{STATE_BRANCH}"
    headers = {"Authorization": f"token {GH_PAT}"} if GH_PAT else {}

    success_count = 0
    for local_name, remote_name in FILE_MAP.items():
        try:
            req = r.Request(f"{base_url}/{remote_name}", headers=headers)
            with r.urlopen(req) as resp:
                # 1. 讀取 Base64 內容
                encoded_data = resp.read()
                # 2. Base64 解碼 -> XOR 解密
                decrypted_data = _crypt(base64.b64decode(encoded_data))
                with open(local_name, "wb") as f:
                    f.write(decrypted_data)
                success_count += 1
                print(f"  🔒 {local_name} 解密還原成功")
        except Exception:
            continue

    return success_count > 0

def up_state():
    """加密並推送狀態至 GitHub"""
    if not all([GH_PAT, GH_OWNER, GH_REPO]): return False
    print(f"🚀 正在加密推送狀態至 {STATE_BRANCH}...")
    
    try:
        tmp_dir = "tmp_state_git"
        if os.path.exists(tmp_dir): subprocess.run(["rm", "-rf", tmp_dir])
        os.makedirs(tmp_dir)

        for local_name, remote_name in FILE_MAP.items():
            if os.path.exists(local_name):
                with open(local_name, "rb") as f:
                    # 1. XOR 加密 -> Base64 編碼
                    encrypted_data = base64.b64encode(_crypt(f.read()))
                with open(os.path.join(tmp_dir, remote_name), "wb") as f:
                    f.write(encrypted_data)

        remote_url = f"https://x-access-token:{GH_PAT}@github.com/{GH_OWNER}/{GH_REPO}.git"
        cmds = [
            ["git", "init"],
            ["git", "config", "user.name", "GitHub Actions"],
            ["git", "config", "user.email", "github-actions@github.com"],
            ["git", "checkout", "-b", STATE_BRANCH],
            ["git", "add", "."],
            ["git", "commit", "-m", "chore: secure sync"],
            ["git", "push", remote_url, STATE_BRANCH, "--force"]
        ]
        for cmd in cmds:
            subprocess.run(cmd, cwd=tmp_dir, capture_output=True)
        
        subprocess.run(["rm", "-rf", tmp_dir])
        print("✅ 加密狀態已成功推送。")
        return True
    except Exception as e:
        print(f"❌ 加密推送失敗: {e}")
        return False

def _init_empty_files():
    if not os.path.exists('processed_videos.txt'):
        with open('processed_videos.txt', 'w') as f: f.write('')
    if not os.path.exists('last_check.txt'):
        with open('last_check.txt', 'w') as f: f.write('')
    if not os.path.exists('subscriptions.json'):
        with open('subscriptions.json', 'w') as f: f.write('{}')

def main():
    if len(sys.argv) < 2: return
    action = sys.argv[1]

    if action == "restore":
        dl_state()
    elif action == "persist":
        up_state()

if __name__ == "__main__":
    main()
