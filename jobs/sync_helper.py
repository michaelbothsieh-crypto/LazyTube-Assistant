"""
狀態同步小幫手 (混淆路徑版)
- 移除加密邏輯以提高系統透明度與穩定性
- 使用混淆檔名保護隱私
"""
import os
import json
import sys
import subprocess
import urllib.request as r
import base64

# 配置
STATE_BRANCH = "state"
GH_OWNER = os.environ.get("GH_REPO_OWNER")
GH_REPO = os.environ.get("GH_REPO_NAME")
GH_PAT = os.environ.get("GH_PAT_WORKFLOW")
# 使用與 StateManager 一致的 HASH
_HASH = base64.b64encode(os.environ.get("TG_WEBHOOK_SECRET", "default").encode()).decode()[:12]

FILE_MAP = {
    "processed_videos.txt": f".sys_vid_cache_{_HASH}",
    "last_check.txt": f".sys_time_sync_{_HASH}",
    "subscriptions.json": f".sys_sub_conf_{_HASH}"
}

def dl_state():
    """從 GitHub 下載混淆狀態檔案"""
    print(f"📡 正在還原狀態 (HASH: {_HASH})...")
    _init_empty_files()

    base_url = f"https://raw.githubusercontent.com/{GH_OWNER}/{GH_REPO}/{STATE_BRANCH}"
    headers = {"Authorization": f"token {GH_PAT}"} if GH_PAT else {}

    success_count = 0
    for local_name, remote_name in FILE_MAP.items():
        url = f"{base_url}/{remote_name}"
        try:
            req = r.Request(url, headers=headers)
            with r.urlopen(req) as resp:
                content = resp.read()
                with open(local_name, "wb") as f:
                    f.write(content)
                success_count += 1
                print(f"  ✅ {local_name} 下載成功")
        except Exception: continue

    return success_count > 0

def up_state():
    """推送混淆狀態至 GitHub"""
    if not all([GH_PAT, GH_OWNER, GH_REPO]): return False
    print(f"🚀 正在同步至 {STATE_BRANCH}...")
    
    try:
        tmp_dir = "tmp_state_git"
        if os.path.exists(tmp_dir): subprocess.run(["rm", "-rf", tmp_dir])
        os.makedirs(tmp_dir)

        for local_name, remote_name in FILE_MAP.items():
            if os.path.exists(local_name):
                subprocess.run(["cp", local_name, os.path.join(tmp_dir, remote_name)])

        remote_url = f"https://x-access-token:{GH_PAT}@github.com/{GH_OWNER}/{GH_REPO}.git"
        cmds = [
            ["git", "init"],
            ["git", "config", "user.name", "GitHub Actions"],
            ["git", "config", "user.email", "github-actions@github.com"],
            ["git", "checkout", "-b", STATE_BRANCH],
            ["git", "add", "."],
            ["git", "commit", "-m", "update state"],
            ["git", "push", remote_url, STATE_BRANCH, "--force"]
        ]
        for cmd in cmds:
            subprocess.run(cmd, cwd=tmp_dir, capture_output=True)
        
        subprocess.run(["rm", "-rf", tmp_dir])
        print("✅ 狀態同步完成。")
        return True
    except Exception: return False

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
