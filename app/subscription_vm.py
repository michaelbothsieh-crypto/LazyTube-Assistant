import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from app.config import Config
from app.youtube import YouTubeService
from api.utils.github_dispatch import dispatch_update_cron_workflow


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
                content = f.read().strip()
                if not content: return {}
                data = json.loads(content)
                if not isinstance(data, dict): return {}
                return data
        except Exception as e:
            print(f"⚠️ 讀取訂閱檔案失敗: {e}")
            return {}

    def _save_subs(self, subs: Dict[str, List[Dict[str, Any]]]) -> None:
        """將訂閱資料保存至本地檔案。"""
        try:
            os.makedirs(os.path.dirname(self.subs_file), exist_ok=True) if os.path.dirname(self.subs_file) else None
            with open(self.subs_file, "w", encoding="utf-8") as f:
                json.dump(subs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 儲存訂閱檔案失敗: {e}")

    @staticmethod
    def snap_preferred_time(hour: int) -> str:
        """
        將使用者指定的小時數對齊到最近的有效時段。
        有效時段 = Config.VALID_PREFERRED_HOURS (台北偶數小時 6,8,10...22)
        回傳格式: "HH:00"
        """
        valid = Config.VALID_PREFERRED_HOURS
        # 找最近的有效小時
        best = min(valid, key=lambda h: abs(h - hour))
        # 距離相同時取較大值（使用者期望的時間不早於指定）
        if abs(best - hour) > 0:
            candidates = [h for h in valid if abs(h - hour) == abs(best - hour)]
            best = max(candidates)
        return f"{best:02d}:00"

    async def subscribe(self, chat_id: str, channel_url: str, custom_prompt: str = "", preferred_time: str = "") -> Dict[str, Any]:
        """
        /// 新增頻道訂閱並同步更新 GitHub 群組 Workflow 檔案
        """
        channel_info = self.yt_service.get_channel_info(channel_url)
        if not channel_info:
            return {"success": False, "message": "找不到該頻道，請確認網址是否正確。"}

        subs = self._load_subs()
        group_subs = subs.get(chat_id, [])

        if any(s["channel_id"] == channel_info["id"] for s in group_subs):
            return {"success": False, "message": f"您已經訂閱過「{channel_info['title']}」了。"}

        # 初始檢查時間回溯 24 小時，以便訂閱後能立刻掃描到最近的新片
        last_check_time = datetime.now(timezone.utc) - timedelta(hours=24)
        new_sub = {
            "channel_id": channel_info["id"],
            "channel_title": channel_info["title"],
            "custom_prompt": custom_prompt,
            "preferred_time": preferred_time,
            "last_check": last_check_time.isoformat(),
            "is_first_run": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        if chat_id not in subs:
            subs[chat_id] = []
        subs[chat_id].append(new_sub)

        self._save_subs(subs)
        await dispatch_update_cron_workflow()

        valid_hours_display = ", ".join(f"{h}" for h in Config.VALID_PREFERRED_HOURS)
        time_msg = f"\n定時檢查：<code>{preferred_time}</code>" if preferred_time else "\n定時檢查：<code>預設 (每 12 小時)</code>"
        return {
            "success": True,
            "channel_id": channel_info["id"],
            "message": f"✅ 已成功訂閱「<b>{channel_info['title']}</b>」！\n"
                       f"🔗 頻道連結：<a href='https://www.youtube.com/channel/{channel_info['id']}'>點此確認</a>\n"
                       f"客製化 Prompt：{custom_prompt if custom_prompt else '（使用預設）'}"
                       f"{time_msg}\n\n"
                       f"🚀 <b>訂閱成功！</b> 稍後將自動啟動第一次掃描。"
        }

    def update_signup_msg_id(self, chat_id: str, channel_id: str, msg_id: str) -> None:
        """紀錄訂閱成功訊息的 ID，以便 Action 執行後清理"""
        subs = self._load_subs()
        if chat_id in subs:
            for s in subs[chat_id]:
                if s["channel_id"] == channel_id:
                    s["signup_msg_id"] = msg_id
                    break
            self._save_subs(subs)

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

        subs[chat_id] = [s for s in subs[chat_id] if s["channel_id"] != target_channel_id]

        self._save_subs(subs)
        await dispatch_update_cron_workflow()
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
                    s["is_first_run"] = False
                    break
            self._save_subs(subs)
