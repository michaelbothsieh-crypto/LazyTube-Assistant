"""
專用的群組任務執行程式 (Group Executor)
由 sub-<chat_id>.yml 呼叫，處理該群組內的所有訂閱。
"""
import sys
import os
from datetime import datetime, timezone, timedelta
from app.auth import AuthManager
from app.config import Config
from app.youtube import YouTubeService
from app.notebook import NotebookService
from app.notifier import Notifier
from app.state_manager import StateManager
from app.subscription_vm import SubscriptionViewModel

def main():
    if len(sys.argv) < 2:
        print("使用方法: python on_demand_group.py <chat_id>")
        sys.exit(1)

    chat_id = sys.argv[1]
    
    # 1. 驗證與憑證
    AuthManager.deploy_credentials()
    
    # 2. 初始化服務
    yt = YouTubeService()
    nb = NotebookService()
    sub_vm = SubscriptionViewModel()
    
    # 3. 獲取該群組的所有訂閱
    all_subs = sub_vm.get_all_active_subscriptions()
    
    # 除錯資訊
    print(f"📊 載入訂閱資料成功，包含群組：{list(all_subs.keys())}")
    group_subs = all_subs.get(chat_id, [])
    
    if not group_subs:
        # 再嘗試一次：萬一 chat_id 類型不匹配
        group_subs = all_subs.get(str(chat_id), []) or all_subs.get(int(chat_id) if str(chat_id).isdigit() else None, [])
    
    if not group_subs:
        print(f"📭 群組 {chat_id} 目前沒有訂閱。")
        return

    now_tw = datetime.now(timezone(timedelta(hours=8)))
    today_str = now_tw.strftime("%Y-%m-%d")
    current_time_str = now_tw.strftime("%H:%M")
    
    print(f"🕒 執行群組任務：{chat_id} (目前時間 TW: {current_time_str})")

    # 4. 遍歷並判斷執行
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
        
        # 判定 A: 有設定時間 (9:30, 10:00...)
        if pref_time:
            # 如果今天還沒跑過，且現在時間已經到了或過了預設時間
            if last_check_day != today_str and current_time_str >= pref_time:
                should_run = True
                print(f"🎯 [定時點] {channel_title} 執行時間已到 ({pref_time})")
        
        # 判定 B: 沒設定時間 (保底模式，每 12 小時檢查一次)
        else:
            if not last_check_str or (datetime.now(timezone.utc) - datetime.fromisoformat(last_check_str)).total_seconds() > 12 * 3600:
                should_run = True
                print(f"⏲️ [保底點] {channel_title} 已超過 12 小時未檢查")

        # 特殊情況：如果是主動觸發的第一次執行，我們也應該讓它跑
        if is_first_run:
            should_run = True

        if not should_run:
            print(f"⏭️ 跳過 {channel_title} (未到執行時間或今日已處理)")
            continue

        # 5. 執行該頻道的摘要邏輯
        try:
            pid_map = yt._get_uploads_playlist_ids([channel_id])
            pid = pid_map.get(channel_id)
            if not pid: continue

            # 第一次執行時只需抓 1 支，後續抓 10 支
            items = yt._get_playlist_items(pid, limit=1 if is_first_run else 10)
            
            for item in items:
                pub_time = datetime.fromisoformat(item["snippet"]["publishedAt"].replace("Z", "+00:00"))
                
                # 如果不是第一次執行，才需要檢查時間是否比上次新
                if not is_first_run and last_check_str and pub_time <= datetime.fromisoformat(last_check_str):
                    continue
                
                vid_id = item["contentDetails"]["videoId"]
                if vid_id in processed_ids: continue
                
                print(f"🎬 處理新影片：{item['snippet']['title']}")
                summary = nb.process_video(f"https://www.youtube.com/watch?v={vid_id}", item['snippet']['title'], custom_prompt=sub.get("custom_prompt"))
                if summary:
                    Notifier.send_summary(item['snippet']['title'], f"https://www.youtube.com/watch?v={vid_id}", channel_title, summary, target_chat_id=chat_id)
                    StateManager.add_processed_id(vid_id)
                
                # 第一次執行只需處理一部
                if is_first_run:
                    break
            
            # 更新該訂閱項目的 last_check
            sub_vm.update_last_check(chat_id, channel_id, datetime.now(timezone.utc))
            
        except Exception as e:
            print(f"❌ 處理頻道 {channel_title} 時發生錯誤: {e}")

    print("✅ 群組任務執行完畢。")

if __name__ == "__main__":
    main()
