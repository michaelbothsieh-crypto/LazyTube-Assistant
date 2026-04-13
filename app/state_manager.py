from datetime import datetime, timedelta, timezone
from app.config import Config
import os
import httpx
import json
import base64
from itertools import cycle

class StateManager:
    """
    /// 狀態管理模組 (GitHub 加密存儲版)
    /// 使用 TG_WEBHOOK_SECRET 作為金鑰，確保 state 分支內容不被肉眼讀取。
    """
    SECRET = os.environ.get("TG_WEBHOOK_SECRET", "default_key")
    FILE_MAP = {
        "processed_videos.txt": ".sys_vid_cache",
        "last_check.txt": ".sys_time_sync",
        "subscriptions.json": ".sys_sub_conf"
    }

    @staticmethod
    def _crypt(data: bytes) -> bytes:
        """使用 XOR 進行簡單加密/解密"""
        return bytes([b ^ k for b, k in zip(data, cycle(StateManager.SECRET.encode()))])

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
        """從 GitHub 下載並解密狀態 (支援 Vercel)"""
        gh_owner = os.environ.get("GH_REPO_OWNER")
        gh_repo = os.environ.get("GH_REPO_NAME")
        gh_pat = os.environ.get("GH_PAT_WORKFLOW")
        
        if not gh_owner or not gh_repo: return False
        
        remote_name = StateManager.FILE_MAP.get(filename, filename)
        local_path = Config.SUBSCRIPTIONS_FILE if filename == "subscriptions.json" else filename
        StateManager.clear_local(filename)

        try:
            t = int(datetime.now().timestamp())
            url = f"https://raw.githubusercontent.com/{gh_owner}/{gh_repo}/state/{remote_name}?t={t}"
            
            headers = {"Authorization": f"token {gh_pat}"} if gh_pat else {}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=15.0)
                if resp.status_code == 200:
                    # 1. Base64 解碼 -> XOR 解密
                    decrypted_data = StateManager._crypt(base64.b64decode(resp.content))
                    os.makedirs(os.path.dirname(local_path), exist_ok=True) if os.path.dirname(local_path) else None
                    with open(local_path, "wb") as f:
                        f.write(decrypted_data)
                    return True
        except Exception: pass
        return False

    @staticmethod
    async def sync_to_blob(filename: str) -> bool:
        """加密並透過 GitHub API 更新 state 分支檔案 (支援 Vercel /sub)"""
        gh_owner = os.environ.get("GH_REPO_OWNER")
        gh_repo = os.environ.get("GH_REPO_NAME")
        gh_pat = os.environ.get("GH_PAT_WORKFLOW")
        
        if not all([gh_owner, gh_repo, gh_pat]): return False
        
        remote_name = StateManager.FILE_MAP.get(filename, filename)
        local_path = Config.SUBSCRIPTIONS_FILE if filename == "subscriptions.json" else filename
        if not os.path.exists(local_path): return False

        try:
            with open(local_path, "rb") as f:
                # 1. XOR 加密 -> Base64 編碼
                encrypted_content = base64.b64encode(StateManager._crypt(f.read())).decode("utf-8")

            api_url = f"https://api.github.com/repos/{gh_owner}/{gh_repo}/contents/{remote_name}?ref=state"
            headers = {"Authorization": f"token {gh_pat}", "Accept": "application/vnd.github+json"}
            
            sha = None
            async with httpx.AsyncClient() as client:
                resp = await client.get(api_url, headers=headers)
                if resp.status_code == 200:
                    sha = resp.json().get("sha")

            payload = {
                "message": "secure update",
                "content": encrypted_content,
                "branch": "state"
            }
            if sha: payload["sha"] = sha

            async with httpx.AsyncClient() as client:
                put_resp = await client.put(api_url, json=payload, headers=headers)
                return put_resp.status_code in [200, 201]
        except Exception: return False
