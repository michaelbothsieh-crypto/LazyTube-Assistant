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

def dl_state():
    """從 GitHub state 分支下載狀態檔案"""
    print(f"📡 正在從 GitHub {GH_OWNER}/{GH_REPO} 的 {STATE_BRANCH} 分支還原狀態...")
    
    # 建立基礎檔案，防止後續出錯
    _init_empty_files()

    base_url = f"https://raw.githubusercontent.com/{GH_OWNER}/{GH_REPO}/{STATE_BRANCH}"
    headers = {}
    if GH_PAT:
        headers["Authorization"] = f"token {GH_PAT}"

    files_to_sync = ["processed_videos.txt", "last_check.txt", "subscriptions.json"]
    success_count = 0

    for filename in files_to_sync:
        url = f"{base_url}/{filename}"
        try:
            req = r.Request(url, headers=headers)
            with r.urlopen(req) as resp:
                content = resp.read()
                with open(filename, "wb") as f:
                    f.write(content)
                success_count += 1
                print(f"  ✅ {filename} 下載完成")
        except Exception as e:
            print(f"  ⚠️ {filename} 下載失敗 (可能是首次執行): {e}")

    if success_count > 0:
        print(f"✨ 狀態還原完成 (共 {success_count} 個檔案)")
        return True
    return False

def up_state():
    """將本地狀態推送到 state 分支 (Orphan + Force Push)"""
    if not all([GH_PAT, GH_OWNER, GH_REPO]):
        print("❌ 缺少 GitHub 環境變數，無法執行同步。")
        return

    print(f"🚀 正在推送狀態至 {STATE_BRANCH} 分支...")
    
    try:
        # 1. 建立一個乾淨的暫存目錄來處理 Git 操作
        tmp_dir = "tmp_state_git"
        if os.path.exists(tmp_dir):
            subprocess.run(["rm", "-rf", tmp_dir])
        os.makedirs(tmp_dir)

        # 2. 複製狀態檔案到暫存目錄
        files_to_sync = ["processed_videos.txt", "last_check.txt", "subscriptions.json"]
        for f in files_to_sync:
            if os.path.exists(f):
                subprocess.run(["cp", f, os.path.join(tmp_dir, f)])
            else:
                # 確保檔案存在，避免 git add 失敗
                with open(os.path.join(tmp_dir, f), "w") as empty_f:
                    empty_f.write("{} " if f.endswith(".json") else "")

        # 3. 初始化 Git 並強制推送
        remote_url = f"https://x-access-token:{GH_PAT}@github.com/{GH_OWNER}/{GH_REPO}.git"
        
        cmds = [
            ["git", "init"],
            ["git", "config", "user.name", "GitHub Actions"],
            ["git", "config", "user.email", "github-actions@github.com"],
            ["git", "checkout", "-b", STATE_BRANCH],
            ["git", "add", "."],
            ["git", "commit", "-m", f"chore: update state at {os.environ.get('GITHUB_RUN_ID', 'manual')}"],
            ["git", "push", remote_url, STATE_BRANCH, "--force"]
        ]

        for cmd in cmds:
            result = subprocess.run(cmd, cwd=tmp_dir, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Git 指令失敗: {' '.join(cmd)}")
                print(f"錯誤訊息: {result.stderr}")
                return False

        print(f"✅ 狀態已成功推送到 {STATE_BRANCH} 分支 (已強制覆蓋，保持 1 個 Commit)")
        
        # 清理
        subprocess.run(["rm", "-rf", tmp_dir])
        return True

    except Exception as e:
        print(f"❌ 同步過程中發生異常: {e}")
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
