"""
podcast_sync_helper.py — Podcast 掃描器的狀態同步小工具。

與 sync_helper.py 相同邏輯，但管理 processed_podcasts.json。
"""
import os
import sys
import subprocess
import urllib.request as r

STATE_BRANCH = "state"
GH_OWNER = os.environ.get("GH_REPO_OWNER")
GH_REPO = os.environ.get("GH_REPO_NAME")
GH_PAT = os.environ.get("GH_PAT_WORKFLOW")

FILE_MAP = {
    "processed_podcasts.json": ".sys_podcast_storage_v1.json",
}


def dl_state():
    print(f"📡 正在從 {STATE_BRANCH} 還原 Podcast 狀態...")
    _init_empty_files()
    base_url = f"https://raw.githubusercontent.com/{GH_OWNER}/{GH_REPO}/{STATE_BRANCH}"
    headers = {"Authorization": f"token {GH_PAT}"} if GH_PAT else {}
    for local_name, remote_name in FILE_MAP.items():
        try:
            req = r.Request(f"{base_url}/{remote_name}", headers=headers)
            with r.urlopen(req) as resp:
                with open(local_name, "wb") as f:
                    f.write(resp.read())
            print(f"  ✅ {local_name} 下載成功")
        except Exception as e:
            print(f"  ⚠️  {local_name} 下載失敗（首次執行正常）：{e}")


def up_state():
    if not all([GH_PAT, GH_OWNER, GH_REPO]):
        print("⚠️  缺少 GitHub 設定，跳過狀態同步")
        return False
    print(f"🚀 正在同步 Podcast 狀態至 {STATE_BRANCH}...")
    try:
        tmp_dir = "tmp_podcast_state_git"
        if os.path.exists(tmp_dir):
            subprocess.run(["rm", "-rf", tmp_dir])
        os.makedirs(tmp_dir)
        for local_name, remote_name in FILE_MAP.items():
            if os.path.exists(local_name):
                subprocess.run(["cp", local_name, os.path.join(tmp_dir, remote_name)])
        remote_url = f"https://x-access-token:{GH_PAT}@github.com/{GH_OWNER}/{GH_REPO}.git"
        cmds = [
            ["git", "init"],
            ["git", "config", "user.name", "GitHub Actions"],
            ["git", "config", "user.email", "github-actions@github.com"],
            ["git", "fetch", remote_url, STATE_BRANCH],
            ["git", "checkout", STATE_BRANCH],
        ]
        for cmd in cmds:
            subprocess.run(cmd, cwd=tmp_dir, capture_output=True)

        # 複製檔案
        for local_name, remote_name in FILE_MAP.items():
            if os.path.exists(local_name):
                subprocess.run(["cp", local_name, os.path.join(tmp_dir, remote_name)])

        push_cmds = [
            ["git", "add", "."],
            ["git", "commit", "-m", "update podcast state", "--allow-empty"],
            ["git", "push", remote_url, STATE_BRANCH, "--force"],
        ]
        for cmd in push_cmds:
            subprocess.run(cmd, cwd=tmp_dir, capture_output=True)
        subprocess.run(["rm", "-rf", tmp_dir])
        print("✅ Podcast 狀態同步完成")
        return True
    except Exception as e:
        print(f"❌ 狀態同步失敗：{e}")
        return False


def _init_empty_files():
    if not os.path.exists("processed_podcasts.json"):
        with open("processed_podcasts.json", "w") as f:
            f.write('{"processed_guids": []}')


def main():
    if len(sys.argv) < 2:
        return
    if sys.argv[1] == "restore":
        dl_state()
    elif sys.argv[1] == "persist":
        up_state()


if __name__ == "__main__":
    main()
