"""
自動根據 subscriptions.json 的 preferred_time 更新 master-scheduler.yml 的 cron 排程。
Taiwan time (UTC+8) → UTC conversion → 產生最小化的 cron 表達式。
"""
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
import re
import subprocess

WORKFLOW_PATH = ".github/workflows/master-scheduler.yml"
CRON_COMMENT = "# ⚠️ 此 cron 由 jobs/update_cron.py 自動管理，請勿手動修改"


def tw_time_to_utc_hour(time_str: str) -> int:
    """Taiwan HH:MM → UTC hour (只取整點，分鐘固定用 :05 避開高峰)"""
    hour = int(time_str.split(":")[0])
    return (hour - 8) % 24


def generate_cron(subscriptions_file: str = "subscriptions.json") -> str:
    """
    讀取所有訂閱的 preferred_time，只在這些時段執行。
    沒有任何 preferred_time → fallback: 5 * * * * (每小時)
    """
    if not os.path.exists(subscriptions_file):
        return "5 * * * *"

    with open(subscriptions_file, "r", encoding="utf-8") as f:
        try:
            subs = json.load(f)
        except Exception:
            return "5 * * * *"

    utc_hours = set()
    for group_subs in subs.values():
        for sub in group_subs:
            pref = sub.get("preferred_time", "")
            if pref:
                utc_hours.add(tw_time_to_utc_hour(pref))

    if not utc_hours:
        return "5 * * * *"

    hours_str = ",".join(str(h) for h in sorted(utc_hours))
    return f"5 {hours_str} * * *"


def update_workflow_cron(cron_expr: str) -> bool:
    """將 cron 寫回 master-scheduler.yml，回傳是否有實際變更。"""
    if not os.path.exists(WORKFLOW_PATH):
        print(f"❌ 找不到 {WORKFLOW_PATH}")
        return False

    with open(WORKFLOW_PATH, "r") as f:
        content = f.read()

    new_content = re.sub(
        r"(    - cron: ')[^']+(')",
        rf"\g<1>{cron_expr}\g<2>",
        content,
    )

    if new_content == content:
        print(f"ℹ️ Cron 無變更：{cron_expr}")
        return False

    with open(WORKFLOW_PATH, "w") as f:
        f.write(new_content)

    print(f"✅ Cron 已更新為：{cron_expr}")
    return True


def git_push(cron_expr: str) -> None:
    subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True)
    subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True)
    subprocess.run(["git", "add", WORKFLOW_PATH], check=True)
    result = subprocess.run(
        ["git", "commit", "-m", f"chore: auto-update scheduler cron to '{cron_expr}'"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("ℹ️ 沒有需要 commit 的變更")
        return
    subprocess.run(["git", "push"], check=True)
    print("🚀 已推送 cron 更新")


if __name__ == "__main__":
    cron = generate_cron()
    print(f"📅 根據訂閱產生 cron：{cron}")
    changed = update_workflow_cron(cron)
    if changed:
        git_push(cron)
