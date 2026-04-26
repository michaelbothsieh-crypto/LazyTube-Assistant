"""
scripts/register_tg_commands.py
================================
向 Telegram Bot API 註冊指令選單（/setMyCommands）。

執行後使用者在 Bot 聊天視窗輸入 / 時，即可看到下拉指令清單與說明。

用法：
    python scripts/register_tg_commands.py

環境變數：
    TELEGRAM_BOT_TOKEN  — Bot Token (必填)
"""
from __future__ import annotations

import os
import sys
import json
import urllib.request as req
import urllib.error


# ── 指令清單定義 ──────────────────────────────────────────────────────────
# 每個 command 最多 32 字元（小寫英數字與底線）
# 每個 description 最多 256 字元
COMMANDS = [
    # YouTube 摘要
    {"command": "nlm",          "description": "🔗 網址摘要分析 (1-3分)"},
    {"command": "note",         "description": "📝 產生詳細 Markdown 報告檔案 (3-5分)"},
    {"command": "batch",        "description": "📦 批次匯入多網址整合摘要 (3-8分)"},
    {"command": "slide",        "description": "📊 產生 PDF/PPTX 簡報 (5-10分)"},
    {"command": "research",     "description": "🔎 深度研究主題並產出網頁報告 (3-10分)"},
    # YouTube 訂閱
    {"command": "sub",          "description": "➕ 訂閱 YouTube 頻道（自動摘要）"},
    {"command": "list",         "description": "📋 查看 YouTube 訂閱清單"},
    {"command": "unsub",        "description": "➖ 取消 YouTube 訂閱"},
    # Podcast
    {"command": "podcast",      "description": "🎙️ 立即分析 Podcast（最新或指定 EP，或 list）"},
    {"command": "subpodcast",   "description": "➕ 訂閱 Podcast 每日自動分析"},
    {"command": "listpodcast",  "description": "📋 查看 Podcast 訂閱清單"},
    {"command": "unsubpodcast", "description": "➖ 取消 Podcast 訂閱"},
    # 系統
    {"command": "help",         "description": "❓ 顯示完整指令說明"},
]


def register(bot_token: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/setMyCommands"
    payload = json.dumps({"commands": COMMANDS}).encode()
    try:
        request = req.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with req.urlopen(request, timeout=15) as resp:
            body = json.loads(resp.read())
            if body.get("ok"):
                print(f"✅ 成功註冊 {len(COMMANDS)} 個指令到 Bot 選單")
                return True
            print(f"❌ API 回傳錯誤：{body}")
            return False
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌ HTTP {e.code}：{body}")
        return False
    except Exception as e:
        print(f"❌ 例外：{e}")
        return False


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("❌ 請設定環境變數 TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    ok = register(token)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
