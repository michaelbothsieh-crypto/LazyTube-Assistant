from datetime import datetime, timedelta, timezone
from app.config import Config
import os
import httpx
import json
import base64

class StateManager:
    """
    /// 狀態管理模組 (GitHub Git-Storage 版)
    /// 替代 Vercel Blob，解決 1000 次額度限制問題。
    """

    @staticmethod
    def get_last_check_time() -> datetime:
        try:
            if os.path.exists(Config.LAST_CHECK_FILE):
                with open(Config.LAST_CHECK_FILE, "r", encoding="utf-8") as f:
                    return datetime.fromisoformat(f.read().strip())
        except Exception: pass
        return datetime.now(timezone.utc) - timedelta(hours=24)

    @staticmethod
    def save_check_time(check_time: datetime) -> None:
        os.makedirs(os.path.dirname(Config.LAST_CHECK_FILE), exist_ok=True) if os.path.dirname(Config.LAST_CHECK_FILE) else None
        with open(Config.LAST_CHECK_FILE, "w", encoding="utf-8") as f:
            f.write(check_time.isoformat())

    @staticmethod
    def get_processed_ids() -> set:
        if not os.path.exists(Config.PROCESSED_VIDEOS_FILE): return set()
        try:
            with open(Config.PROCESSED_VIDEOS_FILE, "r", encoding="utf-8") as f:
                return {line.strip() for line in f if line.strip()}
        except Exception: return set()

    @staticmethod
    def is_processed(video_id: str) -> bool:
        processed_ids = StateManager.get_processed_ids()
        return video_id in processed_ids

    @staticmethod
    def add_processed_id(video_id: str) -> None:
        existing = set()
        ids = []
        if os.path.exists(Config.PROCESSED_VIDEOS_FILE):
            try:
                with open(Config.PROCESSED_VIDEOS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        vid = line.strip()
                        if vid and vid not in existing:
                            ids.append(vid)
                            existing.add(vid)
            except Exception: pass
        if video_id not in existing:
            ids.append(video_id)
        trimmed = ids[-Config.PROCESSED_IDS_LIMIT:]
        os.makedirs(os.path.dirname(Config.PROCESSED_VIDEOS_FILE), exist_ok=True) if os.path.dirname(Config.PROCESSED_VIDEOS_FILE) else None
        with open(Config.PROCESSED_VIDEOS_FILE, "w", encoding="utf-8") as f:
            for vid in trimmed: f.write(f"{vid}\n")

    @staticmethod
    def clear_local(filename: str):
        local_path = Config.SUBSCRIPTIONS_FILE if filename == "subscriptions.json" else filename
        if os.path.exists(local_path):
            try: os.remove(local_path)
            except: pass

    @staticmethod
    async def sync_from_blob(filename: str) -> bool:
        """從 GitHub state 分支下載最新狀態"""
        gh_owner = os.environ.get("GH_REPO_OWNER")
        gh_repo = os.environ.get("GH_REPO_NAME")
        gh_pat = os.environ.get("GH_PAT_WORKFLOW")
        
        if not gh_owner or not gh_repo: return False
        
        local_path = Config.SUBSCRIPTIONS_FILE if filename == "subscriptions.json" else filename
        StateManager.clear_local(filename)

        try:
            # 使用 GitHub Raw URL (具備快取穿透)
            t = int(datetime.now().timestamp())
            url = f"https://raw.githubusercontent.com/{gh_owner}/{gh_repo}/state/{filename}?t={t}"
            
            headers = {}
            if gh_pat:
                headers["Authorization"] = f"token {gh_pat}"

            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=15.0)
                if resp.status_code == 200:
                    os.makedirs(os.path.dirname(local_path), exist_ok=True) if os.path.dirname(local_path) else None
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
                    return True
                else:
                    print(f"⚠️ GitHub 下載失敗 ({filename}): {resp.status_code}")
        except Exception as e:
            print(f"❌ GitHub 同步異常: {e}")
        return False

    @staticmethod
    async def sync_to_blob(filename: str) -> bool:
        """透過 GitHub API 更新 state 分支檔案 (用於 /sub 訂閱)"""
        gh_owner = os.environ.get("GH_REPO_OWNER")
        gh_repo = os.environ.get("GH_REPO_NAME")
        gh_pat = os.environ.get("GH_PAT_WORKFLOW")
        
        if not all([gh_owner, gh_repo, gh_pat]): return False
        
        local_path = Config.SUBSCRIPTIONS_FILE if filename == "subscriptions.json" else filename
        if not os.path.exists(local_path): return False

        try:
            with open(local_path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf-8")

            # 1. 取得目標檔案的 current SHA (如果存在)
            api_url = f"https://api.github.com/repos/{gh_owner}/{gh_repo}/contents/{filename}?ref=state"
            headers = {
                "Authorization": f"token {gh_pat}",
                "Accept": "application/vnd.github+json"
            }
            
            sha = None
            async with httpx.AsyncClient() as client:
                resp = await client.get(api_url, headers=headers)
                if resp.status_code == 200:
                    sha = resp.json().get("sha")

            # 2. 更新或建立檔案
            payload = {
                "message": f"chore: update {filename} from telegram webhook",
                "content": content,
                "branch": "state"
            }
            if sha:
                payload["sha"] = sha

            async with httpx.AsyncClient() as client:
                put_resp = await client.put(api_url, json=payload, headers=headers)
                if put_resp.status_code in [200, 201]:
                    print(f"✅ GitHub '{filename}' 更新成功。")
                    return True
                else:
                    print(f"❌ GitHub API 失敗: {put_resp.status_code} {put_resp.text}")
                    return False
        except Exception as e:
            print(f"❌ GitHub Sync-To 異常: {e}")
        return False
