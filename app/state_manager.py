from datetime import datetime, timedelta, timezone
from app.config import Config
import os
import httpx
import json

class StateManager:
    """
    /// 狀態管理模組
    /// 負責狀態檔案的同步與讀寫邏輯 (具備防快取機制)
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
        # 保持插入順序以確保 trim 時保留最新的
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
            except Exception:
                pass
        if video_id not in existing:
            ids.append(video_id)
        trimmed = ids[-Config.PROCESSED_IDS_LIMIT:]
        os.makedirs(os.path.dirname(Config.PROCESSED_VIDEOS_FILE), exist_ok=True) if os.path.dirname(Config.PROCESSED_VIDEOS_FILE) else None
        with open(Config.PROCESSED_VIDEOS_FILE, "w", encoding="utf-8") as f:
            for vid in trimmed: f.write(f"{vid}\n")

    @staticmethod
    def clear_local(filename: str):
        """強制移除本地暫存檔，確保下次從雲端重新下載"""
        local_path = Config.SUBSCRIPTIONS_FILE if filename == "subscriptions.json" else filename
        if os.path.exists(local_path):
            try: os.remove(local_path)
            except: pass

    @staticmethod
    async def sync_from_blob(filename: str) -> bool:
        """從 Vercel Blob 下載最新狀態 (防快取模式)"""
        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        if not token: return False
        
        local_path = Config.SUBSCRIPTIONS_FILE if filename == "subscriptions.json" else filename
        # 強制清理舊的本地檔案
        StateManager.clear_local(filename)

        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Cache-Control": "no-cache" # 告知 Vercel 不要給快取
            }
            # URL 加入隨機數確保穿透快取
            t = int(datetime.now().timestamp())
            list_url = f"https://blob.vercel-storage.com?prefix=state/{filename}&t={t}"
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(list_url, headers=headers, timeout=10.0)
                if resp.status_code != 200: return False
                
                blobs = resp.json().get("blobs", [])
                if not blobs: return False
                
                # 取得最新的 blob URL 並下載
                file_resp = await client.get(f"{blobs[0]['url']}?t={t}", timeout=15.0)
                if file_resp.status_code == 200:
                    os.makedirs(os.path.dirname(local_path), exist_ok=True) if os.path.dirname(local_path) else None
                    with open(local_path, "wb") as f:
                        f.write(file_resp.content)
                    return True
        except Exception: pass
        return False

    @staticmethod
    async def sync_to_blob(filename: str) -> bool:
        """上傳狀態至 Vercel Blob 並確保覆蓋"""
        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        if not token: return False
        
        local_path = Config.SUBSCRIPTIONS_FILE if filename == "subscriptions.json" else filename
        if not os.path.exists(local_path): return False

        try:
            with open(local_path, "rb") as f:
                data = f.read()
            if len(data) == 0: data = b"\n"

            url = f"https://blob.vercel-storage.com/state/{filename}"
            headers = {
                "Authorization": f"Bearer {token}",
                "x-api-version": "1",
                "x-add-random-suffix": "0",
                "content-type": "application/octet-stream"
            }
            async with httpx.AsyncClient() as client:
                resp = await client.put(url, content=data, headers=headers, timeout=30.0)
                if resp.status_code == 200:
                    print(f"✅ Blob '{filename}' updated successfully.")
                    return True
                else:
                    print(f"❌ Blob update failed: {resp.status_code} {resp.text}")
                    return False
        except Exception as e:
            print(f"❌ Blob sync exception: {e}")
        return False
