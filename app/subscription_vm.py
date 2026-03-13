import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from app.config import Config
from app.youtube import YouTubeService


class SubscriptionViewModel:
    """
    /// 頻道訂閱管理 ViewModel (群組模式)
    /// 負責處理群組對頻道的追蹤，並同步建立對應的 GitHub Group Workflow
    """

    def __init__(self):
        self.yt_service = YouTubeService()
        self.subs_file = Config.SUBSCRIPTIONS_FILE

    def _load_subs(self) -> Dict[str, List[Dict[str, Any]]]:
        """從檔案讀取所有訂閱資料。"""
        if not os.path.exists(self.subs_file):
            return {}
        try:
            with open(self.subs_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_subs(self, subs: Dict[str, List[Dict[str, Any]]]) -> None:
        """將訂閱資料保存至檔案。"""
        with open(self.subs_file, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)

    async def subscribe(self, chat_id: str, channel_url: str, custom_prompt: str = "", preferred_time: str = "") -> Dict[str, Any]:
        """
        /// 新增頻道訂閱並同步更新 GitHub 群組 Workflow 檔案
        """
        channel_info = self.yt_service.get_channel_info(channel_url)
        if not channel_info:
            return {"success": False, "message": "找不到該頻道，請確認網址是否正確。"}

        subs = self._load_subs()
        group_subs = subs.get(chat_id, [])

        # 檢查是否已訂閱過
        if any(s["channel_id"] == channel_info["id"] for s in group_subs):
            return {"success": False, "message": f"您已經訂閱過「{channel_info['title']}」了。"}

        # 更新記憶體中的資料
        # 初始檢查時間回溯 24 小時，以便訂閱後能立刻掃描到最近的新片
        last_check_time = datetime.now(timezone.utc) - timedelta(hours=24)
        new_sub = {
            "channel_id": channel_info["id"],
            "channel_title": channel_info["title"],
            "custom_prompt": custom_prompt,
            "preferred_time": preferred_time,
            "last_check": last_check_time.isoformat(),
            "is_first_run": True, # 標記為第一次執行
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        if chat_id not in subs: subs[chat_id] = []
        subs[chat_id].append(new_sub)

        # 1. 同步建立/更新 GitHub 群組 Workflow
        from api.utils.github_dispatch import update_group_workflow, dispatch_group_workflow
        success = await update_group_workflow(chat_id, subs[chat_id])
        
        if not success:
            return {"success": False, "message": "❌ 同步 GitHub 排程失敗，請檢查 GH_PAT 設定。"}

        # 2. 儲存至檔案
        self._save_subs(subs)
        
        # 3. 自動觸發第一次執行
        # 注意：剛建立的檔案 GitHub 需要幾秒鐘索引，這裡稍作等待後觸發
        from api.utils.github_dispatch import dispatch_group_workflow
        import asyncio
        await asyncio.sleep(3) # 等待 3 秒確保 GitHub 索引完成
        await dispatch_group_workflow(chat_id)

        time_msg = f"\n定時檢查：<code>{preferred_time}</code>" if preferred_time else "\n定時檢查：<code>預設 (每 12 小時)</code>"
        return {
            "success": True, 
            "message": f"✅ 已成功訂閱「{channel_info['title']}」！\n"
                       f"客製化 Prompt：{custom_prompt if custom_prompt else '（使用預設）'}"
                       f"{time_msg}\n\n"
                       f"🚀 <b>已自動啟動第一次掃描</b>，若過去 24 小時內有新片，稍後將發送摘要。"
        }

    async def unsubscribe(self, chat_id: str, channel_id_or_index: str) -> Dict[str, Any]:
        """
        /// 取消訂閱頻道並更新 Workflow 檔案
        """
        subs = self._load_subs()
        if chat_id not in subs or not subs[chat_id]:
            return {"success": False, "message": "目前沒有任何訂閱。"}

        target_channel_id = None
        target_title = ""

        if channel_id_or_index.isdigit():
            idx = int(channel_id_or_index) - 1
            if 0 <= idx < len(subs[chat_id]):
                sub = subs[chat_id][idx]
                target_channel_id = sub["channel_id"]
                target_title = sub["channel_title"]
        else:
            sub = next((s for s in subs[chat_id] if s["channel_id"] == channel_id_or_index), None)
            if sub:
                target_channel_id = sub["channel_id"]
                target_title = sub["channel_title"]

        if not target_channel_id:
            return {"success": False, "message": "找不到該頻道。"}

        # 更新清單紀錄
        subs[chat_id] = [s for s in subs[chat_id] if s["channel_id"] != target_channel_id]
        
        # 1. 同步更新 GitHub Workflow (若無訂閱則刪除檔案)
        from api.utils.github_dispatch import update_group_workflow
        await update_group_workflow(chat_id, subs[chat_id])

        # 2. 儲存
        self._save_subs(subs)
        return {"success": True, "message": f"❌ 已取消訂閱「{target_title}」，群組排程已同步更新。"}

    def list_subscriptions(self, chat_id: str) -> str:
        """列出該群組目前的所有訂閱。"""
        subs = self._load_subs()
        group_subs = subs.get(chat_id, [])
        if not group_subs:
            return "📭 <b>目前沒有訂閱任何頻道</b>"

        msg = f"📋 <b>群組訂閱清單 ({chat_id})：</b>\n\n"
        for i, s in enumerate(group_subs, 1):
            time_info = f" | 🕒 <code>{s['preferred_time']}</code>" if s['preferred_time'] else " | 🕒 <code>預設</code>"
            msg += f"{i}. <b>{s['channel_title']}</b>{time_info}\n"
        
        msg += "\n💡 輸入 <code>/unsub &lt;序號&gt;</code> 可取消訂閱。"
        return msg

    def get_all_active_subscriptions(self) -> Dict[str, List[Dict[str, Any]]]:
        return self._load_subs()

    def update_last_check(self, chat_id: str, channel_id: str, check_time: datetime) -> None:
        subs = self._load_subs()
        if chat_id in subs:
            for s in subs[chat_id]:
                if s["channel_id"] == channel_id:
                    s["last_check"] = check_time.isoformat()
                    s["is_first_run"] = False # 清除第一次執行標記
                    break
            self._save_subs(subs)
