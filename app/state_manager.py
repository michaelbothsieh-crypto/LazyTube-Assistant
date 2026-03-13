from datetime import datetime, timedelta, timezone
from app.config import Config
import os
import httpx
import json

class StateManager:
    """
    /// 狀態管理模組
    /// 封裝狀態檔案的同步與讀寫邏輯
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
    def add_processed_id(video_id: str) -> None:
        ids = list(StateManager.get_processed_ids())
        if video_id not in ids: ids.append(video_id)
        trimmed = ids[-150:]
        os.makedirs(os.path.dirname(Config.PROCESSED_VIDEOS_FILE), exist_ok=True) if os.path.dirname(Config.PROCESSED_VIDEOS_FILE) else None
        with open(Config.PROCESSED_VIDEOS_FILE, "w", encoding="utf-8") as f:
            for vid in trimmed: f.write(f"{vid}\n")

    @staticmethod
    def clear_local(filename: str):
        """移除本地快取的狀態檔案"""
        local_path = ""
        if filename == "subscriptions.json": local_path = Config.SUBSCRIPTIONS_FILE
        elif filename == "last_check.txt": local_path = Config.LAST_CHECK_FILE
        elif filename == "processed_videos.txt": local_path = Config.PROCESSED_VIDEOS_FILE
        else: local_path = filename
        
        if os.path.exists(local_path):
            try: os.remove(local_path)
            except: pass

    @staticmethod
    async def sync_from_blob(filename: str) -> bool:
        """從 Vercel Blob 尋找並下載最新的狀態檔案"""
        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        if not token: return False
        
        local_path = ""
        if filename == "subscriptions.json": local_path = Config.SUBSCRIPTIONS_FILE
        elif filename == "last_check.txt": local_path = Config.LAST_CHECK_FILE
        elif filename == "processed_videos.txt": local_path = Config.PROCESSED_VIDEOS_FILE
        else: local_path = filename

        try:
            headers = {"Authorization": f"Bearer {token}"}
            # 1. 先透過 List API 找到該檔案的真實 URL
            list_url = f"https://blob.vercel-storage.com/v1?prefix=state/{filename}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(list_url, headers=headers, timeout=10.0)
                if resp.status_code != 200: return False
                
                data = resp.json()
                blobs = data.get("blobs", [])
                if not blobs: return False
                
                # 取得最近更新的那個 blob URL
                target_url = blobs[0]["url"]
                
                # 2. 下載真實檔案
                file_resp = await client.get(target_url, timeout=15.0)
                if file_resp.status_code == 200:
                    content = file_resp.content
                    # 預防性檢查：如果是 API 報錯的 JSON 就不寫入
                    if content.startswith(b'{"error":'): return False
                    
                    os.makedirs(os.path.dirname(local_path), exist_ok=True) if os.path.dirname(local_path) else None
                    with open(local_path, "wb") as f:
                        f.write(content)
                    return True
        except Exception: pass
        return False

    @staticmethod
    async def sync_to_blob(filename: str) -> bool:
        """將本地檔案上傳至 Vercel Blob (覆蓋模式)"""
        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        if not token: return False
        
        local_path = ""
        if filename == "subscriptions.json": local_path = Config.SUBSCRIPTIONS_FILE
        elif filename == "last_check.txt": local_path = Config.LAST_CHECK_FILE
        elif filename == "processed_videos.txt": local_path = Config.PROCESSED_VIDEOS_FILE
        else: local_path = filename

        if not os.path.exists(local_path): return False

        try:
            # 確保內容不是錯誤格式
            if filename.endswith(".json"):
                with open(local_path, "r") as f:
                    test_data = json.load(f)
                    if "error" in test_data and len(test_data) == 1: return False

            url = f"https://blob.vercel-storage.com/v1/upload/state/{filename}"
            with open(local_path, "rb") as f:
                data = f.read()
            
            headers = {
                "Authorization": f"Bearer {token}",
                "x-api-version": "1",
                "x-add-random-suffix": "0", # 禁止隨機後綴以保持路徑穩定
                "content-type": "application/octet-stream"
            }
            async with httpx.AsyncClient() as client:
                resp = await client.put(url, content=data, headers=headers, timeout=30.0)
                return resp.status_code == 200
        except Exception: pass
        return False
