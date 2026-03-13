from datetime import datetime, timedelta, timezone
from app.config import Config


class StateManager:
    """
    /// 狀態管理模組
    /// 封裝 last_check.txt 與 processed_videos.txt 的所有讀寫操作
    """

    @staticmethod
    def get_last_check_time() -> datetime:
        """讀取上次檢查時間，若遺失則回看最近 24 小時。"""
        try:
            import os
            if os.path.exists(Config.LAST_CHECK_FILE):
                with open(Config.LAST_CHECK_FILE, "r", encoding="utf-8") as f:
                    return datetime.fromisoformat(f.read().strip())
        except Exception:
            pass
        return datetime.now(timezone.utc) - timedelta(hours=24)

    @staticmethod
    def save_check_time(check_time: datetime) -> None:
        """持久化檢查時間至檔案。"""
        with open(Config.LAST_CHECK_FILE, "w", encoding="utf-8") as f:
            f.write(check_time.isoformat())

    @staticmethod
    def get_processed_ids() -> set:
        """讀取近期已處理的影片 ID 集合。"""
        import os
        if not os.path.exists(Config.PROCESSED_VIDEOS_FILE):
            return set()
        try:
            with open(Config.PROCESSED_VIDEOS_FILE, "r", encoding="utf-8") as f:
                return {line.strip() for line in f if line.strip()}
        except Exception:
            return set()

    @staticmethod
    def add_processed_id(video_id: str) -> None:
        """紀錄影片 ID 已處理，並保留最近 150 筆。"""
        ids = list(StateManager.get_processed_ids())
        if video_id not in ids:
            ids.append(video_id)
        trimmed = ids[-150:]
        with open(Config.PROCESSED_VIDEOS_FILE, "w", encoding="utf-8") as f:
            for vid in trimmed:
                f.write(f"{vid}\n")

    @staticmethod
    async def sync_from_blob(filename: str) -> bool:
        """從 Vercel Blob 下載指定的狀態檔案"""
        import os
        import httpx
        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        if not token: return False
        
        local_path = ""
        if filename == "subscriptions.json": local_path = Config.SUBSCRIPTIONS_FILE
        elif filename == "last_check.txt": local_path = Config.LAST_CHECK_FILE
        elif filename == "processed_videos.txt": local_path = Config.PROCESSED_VIDEOS_FILE
        else: local_path = filename

        try:
            # 加上時間戳防止緩存
            url = f"https://blob.vercel-storage.com/state/{filename}?t={int(datetime.now().timestamp())}"
            headers = {"Authorization": f"Bearer {token}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=15.0)
                if resp.status_code == 200:
                    os.makedirs(os.path.dirname(local_path), exist_ok=True) if os.path.dirname(local_path) else None
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
                    return True
        except Exception: pass
        return False

    @staticmethod
    async def sync_to_blob(filename: str) -> bool:
        """將本地檔案同步上傳至 Vercel Blob"""
        import os
        import httpx
        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        if not token: return False
        
        local_path = ""
        if filename == "subscriptions.json": local_path = Config.SUBSCRIPTIONS_FILE
        elif filename == "last_check.txt": local_path = Config.LAST_CHECK_FILE
        elif filename == "processed_videos.txt": local_path = Config.PROCESSED_VIDEOS_FILE
        else: local_path = filename

        if not os.path.exists(local_path): return False

        try:
            url = f"https://blob.vercel-storage.com/state/{filename}"
            with open(local_path, "rb") as f:
                data = f.read()
            
            headers = {
                "Authorization": f"Bearer {token}",
                "x-api-version": "1", # 補齊版本號
                "x-add-random-suffix": "0",
                "content-type": "application/octet-stream"
            }
            async with httpx.AsyncClient() as client:
                resp = await client.put(url, content=data, headers=headers, timeout=30.0)
                return resp.status_code == 200
        except Exception: pass
        return False
