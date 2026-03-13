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
