import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import os
import json
import asyncio
from datetime import datetime, timezone, timedelta
from api.utils.github_dispatch import dispatch_group_workflow

async def main():
    if not os.path.exists("subscriptions.json"):
        print("沒有找到 subscriptions.json，跳過排程。")
        return

    with open("subscriptions.json", "r", encoding="utf-8") as f:
        try:
            subs = json.load(f)
        except Exception as e:
            print(f"解析 JSON 失敗: {e}")
            return

    now_tw = datetime.now(timezone(timedelta(hours=8)))
    today_str = now_tw.strftime("%Y-%m-%d")
    current_time_str = now_tw.strftime("%H:%M")
    
    print(f"🕒 目前台灣時間：{now_tw.strftime('%Y-%m-%d %H:%M:%S')}")

    groups_to_dispatch = []

    for chat_id, group_subs in subs.items():
        should_run_group = False
        
        for sub in group_subs:
            pref_time = sub.get("preferred_time")
            last_check_str = sub.get("last_check")
            is_first_run = sub.get("is_first_run", False)
            
            if is_first_run:
                should_run_group = True
                break

            last_check_day = ""
            if last_check_str:
                last_check_day = datetime.fromisoformat(last_check_str).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

            if pref_time:
                # 只有當今天還沒檢查過，且現在時間大於等於預定時間時才觸發
                if last_check_day != today_str and current_time_str >= pref_time:
                    should_run_group = True
                    break
            else:
                # 如果沒有預定時間，預設每 12 小時觸發一次
                if not last_check_str or (datetime.now(timezone.utc) - datetime.fromisoformat(last_check_str)).total_seconds() > 12 * 3600:
                    should_run_group = True
                    break
        
        if should_run_group:
            groups_to_dispatch.append(chat_id)

    if not groups_to_dispatch:
        print("✅ 目前沒有需要執行的群組任務。")
        return

    print(f"🚀 準備觸發以下群組：{groups_to_dispatch}")
    for chat_id in groups_to_dispatch:
        success = await dispatch_group_workflow(chat_id)
        if success:
            print(f"✅ 成功觸發群組 {chat_id}")
        else:
            print(f"❌ 觸發群組 {chat_id} 失敗")

if __name__ == "__main__":
    asyncio.run(main())
