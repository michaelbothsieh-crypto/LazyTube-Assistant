import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
import sys

from app.auth import AuthManager
from app.notebook import NotebookService


def main():
    """
    /// 自動清理 NotebookLM 中遺留的暫存筆記本
    /// 清理對象：名稱開頭為 YT_ / SLIDE_DECK_ / INFOGRAPHIC_ / REPORT_ 的暫存筆記本
    """
    print("🧹 開始執行 NotebookLM 自動清理任務...")

    if not AuthManager.deploy_credentials():
        print("❌ 憑證初始化失敗，無法連線至 NotebookLM。")
        sys.exit(1)

    try:
        res = NotebookService.run_nlm("notebook", "list", "--json")
        if res.returncode != 0:
            print("❌ 無法取得筆記本清單。")
            sys.exit(1)

        notebooks = json.loads(res.stdout) if res.stdout.strip() else []
        if not isinstance(notebooks, list):
            print(f"⚠️ 回傳格式非預期：{res.stdout[:200]}")
            sys.exit(1)

        target_prefixes = ("YT_", "SLIDE_DECK_", "INFOGRAPHIC_", "REPORT_")
        deleted_count = 0

        for nb in notebooks:
            name = nb.get("title", "")
            nb_id = nb.get("notebookId") or nb.get("id", "")

            if not any(name.startswith(prefix) for prefix in target_prefixes):
                continue

            print(f"🗑️ 正在刪除：{name} ({nb_id})")
            del_res = NotebookService.run_nlm("notebook", "delete", nb_id, "--confirm")
            if del_res.returncode == 0:
                deleted_count += 1
            else:
                print(f"⚠️ 刪除失敗：{name}")

        print(f"✨ 清理完成，共刪除 {deleted_count} 個遺留筆記本。")

    except json.JSONDecodeError as e:
        print(f"❌ 解析筆記本清單 JSON 失敗: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 清理過程中發生異常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
