"""
jobs/state_sync.py — 通用 GitHub state branch 狀態同步工具。

替代 sync_helper.py 與 podcast_sync_helper.py 的重複邏輯，
提供統一的 StateSyncer class，由各 helper 傳入各自的 file_map 即可。

用法：
    from jobs.state_sync import StateSyncer
    syncer = StateSyncer({"local.json": ".remote_name.json"})
    syncer.restore()   # 從 state branch 還原
    syncer.persist()   # 寫回 state branch
"""
from __future__ import annotations

import os
import subprocess
import sys
import urllib.request as urllib_req


STATE_BRANCH = "state"


class StateSyncer:
    """
    通用 GitHub state branch 同步器。

    Parameters
    ----------
    file_map : dict[str, str]
        local_filename -> remote_filename 的對應表。
        remote_filename 是 state branch 上儲存的混淆路徑，
        例如 {"processed_podcasts.json": ".sys_podcast_storage_v1.json"}。
    tmp_prefix : str
        暫存 git clone 的目錄前綴，避免多個 job 同時執行時衝突。
    empty_defaults : dict[str, str]
        首次執行時若本地檔案不存在，所使用的預設內容。
        key 為 local_filename，value 為初始內容字串。
    """

    def __init__(
        self,
        file_map: dict[str, str],
        tmp_prefix: str = "tmp_state_git",
        empty_defaults: dict[str, str] | None = None,
    ):
        self.file_map = file_map
        self.tmp_prefix = tmp_prefix
        self.empty_defaults = empty_defaults or {}
        self._gh_owner = os.environ.get("GH_REPO_OWNER")
        self._gh_repo = os.environ.get("GH_REPO_NAME")
        self._gh_pat = os.environ.get("GH_PAT_WORKFLOW")

    # ── 還原 ─────────────────────────────────────────────────────────────

    def restore(self) -> bool:
        """從 state branch 下載所有檔案到本地。"""
        print(f"📡 正在從 {STATE_BRANCH} 還原狀態...")
        self._init_empty_files()
        base_url = (
            f"https://raw.githubusercontent.com/"
            f"{self._gh_owner}/{self._gh_repo}/{STATE_BRANCH}"
        )
        headers = {"Authorization": f"token {self._gh_pat}"} if self._gh_pat else {}
        success_count = 0
        for local_name, remote_name in self.file_map.items():
            try:
                req = urllib_req.Request(f"{base_url}/{remote_name}", headers=headers)
                with urllib_req.urlopen(req) as resp:
                    with open(local_name, "wb") as f:
                        f.write(resp.read())
                print(f"  ✅ {local_name} 下載成功")
                success_count += 1
            except Exception as e:
                print(f"  ⚠️  {local_name} 下載失敗（首次執行正常）：{e}")
        return success_count > 0

    # ── 持久化 ───────────────────────────────────────────────────────────

    def persist(self) -> bool:
        """將本地檔案推送回 state branch。"""
        if not all([self._gh_pat, self._gh_owner, self._gh_repo]):
            print("⚠️  缺少 GitHub 設定，跳過狀態同步")
            return False
        print(f"🚀 正在同步至 {STATE_BRANCH}...")
        tmp_dir = self.tmp_prefix
        try:
            if os.path.exists(tmp_dir):
                subprocess.run(["rm", "-rf", tmp_dir], check=False)
            os.makedirs(tmp_dir)

            # 複製檔案到暫存目錄
            for local_name, remote_name in self.file_map.items():
                if os.path.exists(local_name):
                    subprocess.run(
                        ["cp", local_name, os.path.join(tmp_dir, remote_name)],
                        check=False,
                    )

            remote_url = (
                f"https://x-access-token:{self._gh_pat}"
                f"@github.com/{self._gh_owner}/{self._gh_repo}.git"
            )
            init_cmds = [
                ["git", "init"],
                ["git", "config", "user.name", "GitHub Actions"],
                ["git", "config", "user.email", "github-actions@github.com"],
                ["git", "fetch", remote_url, STATE_BRANCH],
                ["git", "checkout", STATE_BRANCH],
            ]
            for cmd in init_cmds:
                subprocess.run(cmd, cwd=tmp_dir, capture_output=True, check=False)

            # 再次複製（確保 checkout 後覆蓋）
            for local_name, remote_name in self.file_map.items():
                if os.path.exists(local_name):
                    subprocess.run(
                        ["cp", local_name, os.path.join(tmp_dir, remote_name)],
                        check=False,
                    )

            push_cmds = [
                ["git", "add", "."],
                ["git", "commit", "-m", "update state", "--allow-empty"],
                ["git", "push", remote_url, STATE_BRANCH, "--force"],
            ]
            for cmd in push_cmds:
                subprocess.run(cmd, cwd=tmp_dir, capture_output=True, check=False)

            print("✅ 狀態同步完成")
            return True
        except Exception as e:
            print(f"❌ 狀態同步失敗：{e}")
            return False
        finally:
            subprocess.run(["rm", "-rf", tmp_dir], check=False)

    # ── 內部工具 ─────────────────────────────────────────────────────────

    def _init_empty_files(self) -> None:
        """首次執行時，建立本地空白檔案避免後續讀取失敗。"""
        for local_name in self.file_map:
            if not os.path.exists(local_name):
                default_content = self.empty_defaults.get(local_name, "")
                with open(local_name, "w", encoding="utf-8") as f:
                    f.write(default_content)


def _make_cli(syncer: StateSyncer) -> None:
    """通用 CLI 入口，供各 helper 的 main() 使用。"""
    if len(sys.argv) < 2:
        return
    if sys.argv[1] == "restore":
        syncer.restore()
    elif sys.argv[1] == "persist":
        syncer.persist()
