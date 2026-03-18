"""
專用的群組任務執行程式 (Group Executor)
由 execute-group.yml 呼叫，處理該群組內的所有訂閱。
"""
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import hashlib
from datetime import datetime, timezone, timedelta
from app.auth import AuthManager
from app.youtube import YouTubeService
from app.notebook import NotebookService
from app.notifier import Notifier
from app.state_manager import StateManager
from app.subscription_vm import SubscriptionViewModel

def get_h(cid):
    """產出與 github_dispatch 一致的雜湊 ID"""
    return hashlib.sha256(str(cid).encode()).hexdigest()[:12]

def main():
    if len(sys.argv) < 2:
        print("使用方法: python on_demand_group.py <chat_id>")
        sys.exit(1)

    target_chat_id = str(sys.argv[1])

    AuthManager.deploy_credentials()

    yt = YouTubeService()
    nb = NotebookService()
    sub_vm = SubscriptionViewModel()

    # 從雲端同步最新的訂閱狀態
    all_subs = sub_vm.get_all_active_subscriptions()

    if target_chat_id not in all_subs:
        print(f"❌ 找不到群組 {target_chat_id} 的訂閱設定")
        # 列出前 8 碼以供除錯
        print(f"📊 目前資料庫中包含：{[k[:8] for k in all_subs.keys()]}")
        return

    print(f"🎯 群組匹配成功！執行任務中... (ID: {target_chat_id[:8]}...)")
    group_subs = all_subs.get(target_chat_id, [])

    now_tw = datetime.now(timezone(timedelta(hours=8)))
    today_str = now_tw.strftime("%Y-%m-%d")
    current_time_str = now_tw.strftime("%H:%M")
    processed_ids = StateManager.get_processed_ids()

    for sub in group_subs:
        channel_id = sub["channel_id"]
        channel_title = sub["channel_title"]
        pref_time = sub.get("preferred_time")
        last_check_str = sub.get("last_check")
        is_first_run = sub.get("is_first_run", False)

        last_check_day = ""
        if last_check_str:
            last_check_day = datetime.fromisoformat(last_check_str).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

        should_run = False
        if is_first_run:
            should_run = True
        elif pref_time:
            if last_check_day != today_str and current_time_str >= pref_time:
                should_run = True
        else:
            if not last_check_str or (datetime.now(timezone.utc) - datetime.fromisoformat(last_check_str)).total_seconds() > 12 * 3600:
                should_run = True

        if not should_run:
            print(f"⏭️ 跳過 {channel_title} (未到時間或今日已處理)")
            continue

        try:
            pid_map = yt._get_uploads_playlist_ids([channel_id])
            pid = pid_map.get(channel_id)
            if not pid:
                continue

            # 首次執行只取 1 支影片，一般執行最多取 10 支
            items = yt._get_playlist_items(pid, limit=1 if is_first_run else 10)

            for item in items:
                pub_time = datetime.fromisoformat(item["snippet"]["publishedAt"].replace("Z", "+00:00"))
                if not is_first_run and last_check_str and pub_time <= datetime.fromisoformat(last_check_str):
                    continue

                vid_id = item["contentDetails"]["videoId"]
                if vid_id in processed_ids:
                    continue

                print(f"🎬 處理新影片：{item['snippet']['title']}")
                summary = nb.process_video(f"https://www.youtube.com/watch?v={vid_id}", item['snippet']['title'], custom_prompt=sub.get("custom_prompt"))
                if summary:
                    Notifier.send_summary(item['snippet']['title'], f"https://www.youtube.com/watch?v={vid_id}", channel_title, summary, target_chat_id=target_chat_id)
                    StateManager.add_processed_id(vid_id)
                
                # 首次執行只處理一支最新的
                if is_first_run:
                    break

            # 成功處理後，將 is_first_run 設為 False 並更新 last_check
            sub_vm.update_last_check(target_chat_id, channel_id, datetime.now(timezone.utc))

            # 清理訂閱成功訊息 (保持群組乾淨)
            signup_msg_id = sub.get("signup_msg_id")
            if signup_msg_id:
                print(f"🧹 正在清理訂閱通知訊息：{signup_msg_id}")
                Notifier.delete_pending_message(target_chat_id, signup_msg_id)

        except Exception as e:
            print(f"❌ 處理頻道 {channel_title} 時發生錯誤: {e}")

    print("✅ 任務執行完畢。")

if __name__ == "__main__":
    main()
