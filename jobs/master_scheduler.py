import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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

    # 驗證 GitHub dispatch 所需的環境變數
    gh_pat = os.environ.get("GH_PAT_WORKFLOW")
    gh_owner = os.environ.get("GH_REPO_OWNER")
    gh_repo = os.environ.get("GH_REPO_NAME")
    if not all([gh_pat, gh_owner, gh_repo]):
        missing = [k for k, v in {"GH_PAT_WORKFLOW": gh_pat, "GH_REPO_OWNER": gh_owner, "GH_REPO_NAME": gh_repo}.items() if not v]
        print(f"❌ 缺少必要的 GitHub secrets: {', '.join(missing)}")
        print("請到 GitHub → Settings → Secrets and variables → Actions 設定")
        return

    now_tw = datetime.now(timezone(timedelta(hours=8)))
    today_str = now_tw.strftime("%Y-%m-%d")
    current_time_str = now_tw.strftime("%H:%M")

    print(f"🕒 目前台灣時間：{now_tw.strftime('%Y-%m-%d %H:%M:%S')}")

    groups_to_dispatch = []

    for chat_id, group_subs in subs.items():
        should_run_group = False
        trigger_reason = ""

        for sub in group_subs:
            pref_time = sub.get("preferred_time")
            last_check_str = sub.get("last_check")
            is_first_run = sub.get("is_first_run", False)
            channel_title = sub.get("channel_title", "unknown")

            if is_first_run:
                should_run_group = True
                trigger_reason = f"首次執行 ({channel_title})"
                break

            last_check_day = ""
            if last_check_str:
                last_check_day = datetime.fromisoformat(last_check_str).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

            if pref_time:
                # 只要今日尚未跑過且現在時間已過設定時間，就觸發
                if last_check_day != today_str and current_time_str >= pref_time:
                    should_run_group = True
                    trigger_reason = f"定時觸發 (設定: {pref_time}, 現在: {current_time_str})"
                    break
            else:
                # 無設定時間者，維持 12 小時檢查一次
                if not last_check_str or (datetime.now(timezone.utc) - datetime.fromisoformat(last_check_str)).total_seconds() > 12 * 3600:
                    should_run_group = True
                    trigger_reason = f"逾時觸發 ({channel_title})"
                    break

        if should_run_group:
            groups_to_dispatch.append((chat_id, trigger_reason))

    if not groups_to_dispatch:
        print("✅ 目前沒有需要執行的群組任務。")
        return

    print(f"🚀 準備觸發 {len(groups_to_dispatch)} 個群組：")
    for chat_id, reason in groups_to_dispatch:
        print(f"  → {chat_id[:8]}... | 原因: {reason}")
        success = await dispatch_group_workflow(chat_id)
        if success:
            print(f"  ✅ 成功觸發")
        else:
            print(f"  ❌ 觸發失敗！請檢查 GH_PAT_WORKFLOW 是否有 workflow scope")

if __name__ == "__main__":
    asyncio.run(main())
