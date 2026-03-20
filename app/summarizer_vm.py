import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.config import Config
from app.state_manager import StateManager
from app.youtube import YouTubeService
from app.notebook import NotebookService
from app.notifier import Notifier


class SummarizerViewModel:
    """
    /// YouTube 摘要器 ViewModel
    /// 負責處理影片掃描、摘要生成與狀態同步的核心業務邏輯
    """

    def __init__(self):
        self.yt_service = YouTubeService()
        self.notebook_service = NotebookService()
        self.last_check = StateManager.get_last_check_time()
        self.current_time = datetime.now(timezone.utc)
        self.processed_ids = StateManager.get_processed_ids()

    def get_time_range_display(self) -> str:
        """獲取檢查時間區間的在地化顯示字串。"""
        def format_time(dt):
            from datetime import timedelta
            return dt.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
        
        return f"{format_time(self.last_check)} 到 {format_time(self.current_time)}"

    def run_sync(self, target_chat_id: Optional[str] = None) -> Dict[str, int]:
        """
        /// 執行完整的掃描與摘要流程
        /// - 獲取新影片
        /// - 進行去重與篩選
        /// - 批次處理摘要生成
        /// - 更新檢查點狀態
        """
        results = {"success": 0, "skipped": 0, "failed": 0}

        # 1. 獲取新影片
        new_videos = self.yt_service.fetch_new_game_videos(self.last_check)
        if not new_videos:
            StateManager.save_check_time(self.current_time)
            return results

        # 2. 去重與排序 (確保處理最舊到最新的影片)
        unique_to_process = []
        for v in new_videos:
            if v["video_id"] in self.processed_ids:
                results["skipped"] += 1
                continue
            unique_to_process.append(v)

        if not unique_to_process:
            StateManager.save_check_time(self.current_time)
            return results

        # 3. 限制處理數量並開始摘要流程
        videos_batch = unique_to_process[:Config.MAX_VIDEOS]
        
        for video in videos_batch:
            print(f"🎬 處理中：{video['title']}")
            summary = self.notebook_service.process_video(video["url"], video["title"], custom_prompt=Config.CUSTOM_PROMPT)
            
            if summary:
                if summary.startswith("❌"):
                    results["failed"] += 1
                    print(f"⚠️ 略過：{video['title']} (生成失敗: {summary})")
                    continue

                # 發送通知 (View Layer)
                Notifier.send_summary(
                    video["title"],
                    video["url"],
                    video["channel"],
                    summary,
                    target_chat_id=target_chat_id
                )
                # 持久化狀態 (Model/State Layer)
                StateManager.add_processed_id(video["video_id"])
                results["success"] += 1
                print(f"✅ 完成：{video['title']}")
            else:
                results["failed"] += 1
                print(f"⚠️ 略過：{video['title']} (生成失敗: 回傳 None)")

        # 4. 更新全域檢查點
        # 即便本輪有失敗，我們也推進檢查點，避免下次重複掃描同樣的失敗影片造成無限迴圈
        StateManager.save_check_time(self.current_time)
        return results
