from datetime import datetime, timedelta, timezone
from app.config import Config
import os
import httpx
import json
import base64

class StateManager:
    """
    /// 狀態管理模組 (GitHub 穩定混淆路徑版)
    /// 使用固定混淆路徑保護隱私，並確保跨平台讀取的一致性。
    """
    # 使用固定混淆字串作為檔名一部分
    FILE_MAP = {
        "processed_videos.txt": ".sys_vid_storage_v1.txt",
        "last_check.txt": ".sys_time_marker_v1.txt",
        "subscriptions.json": ".sys_subs_config_v1.json"
    }

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
        return video_id in StateManager.get_processed_ids()

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
                            ids.append(vid); existing.add(vid)
            except Exception: pass
        if video_id not in existing: ids.append(video_id)
        trimmed = ids[-Config.PROCESSED_IDS_LIMIT:]
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
        gh_owner = os.environ.get("GH_REPO_OWNER")
        gh_repo = os.environ.get("GH_REPO_NAME")
        gh_pat = os.environ.get("GH_PAT_WORKFLOW")
        if not gh_owner or not gh_repo:
            print(f"⚠️ 同步失敗：缺少環境變數 (Owner: {gh_owner}, Repo: {gh_repo})")
            return False
        
        remote_name = StateManager.FILE_MAP.get(filename, filename)
        local_path = Config.SUBSCRIPTIONS_FILE if filename == "subscriptions.json" else filename

        try:
            # 💡 改用 GitHub API 直接獲取內容 (Immediate consistency)
            # 避開 raw.githubusercontent.com 的數分鐘緩存延遲
            api_url = f"https://api.github.com/repos/{gh_owner}/{gh_repo}/contents/{remote_name}?ref=state"
            headers = {
                "Authorization": f"token {gh_pat}",
                "Accept": "application/vnd.github+json"
            }
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(api_url, headers=headers, timeout=15.0)
                
                if resp.status_code == 200:
                    data = resp.json()
                    content_b64 = data.get("content", "")
                    content = base64.b64decode(content_b64)
                    with open(local_path, "wb") as f:
                        f.write(content)
                    return True
                elif resp.status_code == 404:
                    # 💡 遠端沒檔案時，強制初始化本地檔案，防止讀取到舊請求的殘留資料
                    initial_content = "{}" if filename.endswith(".json") else ""
                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write(initial_content)
                    return True
                else:
                    print(f"❌ API 同步錯誤：{filename} (Status: {resp.status_code})")
        except Exception as e:
            print(f"❌ API 同步異常：{e}")
        return False

    @staticmethod
    async def sync_to_blob(filename: str) -> bool:
        gh_owner = os.environ.get("GH_REPO_OWNER")
        gh_repo = os.environ.get("GH_REPO_NAME")
        gh_pat = os.environ.get("GH_PAT_WORKFLOW")
        if not all([gh_owner, gh_repo, gh_pat]):
            print("⚠️ 上傳失敗：缺少 GitHub 認證設定")
            return False
        
        remote_name = StateManager.FILE_MAP.get(filename, filename)
        local_path = Config.SUBSCRIPTIONS_FILE if filename == "subscriptions.json" else filename
        if not os.path.exists(local_path): return False

        try:
            with open(local_path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf-8")
            api_url = f"https://api.github.com/repos/{gh_owner}/{gh_repo}/contents/{remote_name}?ref=state"
            headers = {"Authorization": f"token {gh_pat}", "Accept": "application/vnd.github+json"}
            sha = None
            async with httpx.AsyncClient() as client:
                resp = await client.get(api_url, headers=headers)
                if resp.status_code == 200: sha = resp.json().get("sha")
            
            payload = {"message": f"sync {filename}", "content": content, "branch": "state"}
            if sha: payload["sha"] = sha
            
            async with httpx.AsyncClient() as client:
                put_resp = await client.put(api_url, json=payload, headers=headers)
                if put_resp.status_code in [200, 201]:
                    return True
                else:
                    print(f"❌ 上傳失敗：{filename} (Status: {put_resp.status_code}, {put_resp.text})")
        except Exception as e:
            print(f"❌ 上傳異常：{e}")
        return False
