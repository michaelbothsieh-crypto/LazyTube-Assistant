"""
狀態同步小幫手 (穩定混淆路徑版)
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

FILE_MAP = {
    "processed_videos.txt": ".sys_vid_storage_v1.txt",
    "last_check.txt": ".sys_time_marker_v1.txt",
    "subscriptions.json": ".sys_subs_config_v1.json"
}

def dl_state():
    print(f"📡 正在從 {STATE_BRANCH} 還原狀態...")
    _init_empty_files()
    base_url = f"https://raw.githubusercontent.com/{GH_OWNER}/{GH_REPO}/{STATE_BRANCH}"
    headers = {"Authorization": f"token {GH_PAT}"} if GH_PAT else {}
    success_count = 0
    for local_name, remote_name in FILE_MAP.items():
        try:
            req = r.Request(f"{base_url}/{remote_name}", headers=headers)
            with r.urlopen(req) as resp:
                with open(local_name, "wb") as f: f.write(resp.read())
                success_count += 1
                print(f"  ✅ {local_name} 下載成功")
        except: continue
    return success_count > 0

def up_state():
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
        for cmd in cmds: subprocess.run(cmd, cwd=tmp_dir, capture_output=True)
        subprocess.run(["rm", "-rf", tmp_dir])
        print("✅ 狀態同步完成。")
        return True
    except: return False

def _init_empty_files():
    for f in ["processed_videos.txt", "last_check.txt"]:
        if not os.path.exists(f):
            with open(f, "w") as x: x.write("")
    if not os.path.exists("subscriptions.json"):
        with open("subscriptions.json", "w") as x: x.write("{}")

def main():
    if len(sys.argv) < 2: return
    if sys.argv[1] == "restore": dl_state()
    elif sys.argv[1] == "persist": up_state()

if __name__ == "__main__": main()
