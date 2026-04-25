"""
app/podcast_state.py — Podcast 訂閱清單與去重狀態的集中管理。

狀態檔案格式 (processed_podcasts.json)：
{
  "subscriptions": {
    "<rss_url>": {"label": "股癌", "added_at": "2026-04-25T09:00:00"}
  },
  "processed": {
    "<rss_url>|<chat_id>": ["guid1", "guid2", ...]
  }
}

設計原則：
- processed 以 (rss_url, chat_id) 為複合 key。
- 確保「同一 TG/LINE 頻道」不會重複收到同一集，
  但不同頻道/群組各自獨立，互不影響。
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

PODCAST_STATE_FILE = "processed_podcasts.json"


def _load_state() -> dict[str, Any]:
    """讀取完整狀態檔案，若不存在則回傳空結構。"""
    if not os.path.exists(PODCAST_STATE_FILE):
        return {"subscriptions": {}, "processed": {}}
    try:
        with open(PODCAST_STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        # 舊格式相容（只有 processed_guids list）
        if "processed_guids" in data:
            return {"subscriptions": {}, "processed": {}}
        return data
    except Exception:
        return {"subscriptions": {}, "processed": {}}


def _save_state(state: dict[str, Any]) -> None:
    with open(PODCAST_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ── 訂閱管理 ──────────────────────────────────────────────────────────────

def get_subscriptions() -> dict[str, dict]:
    """回傳 {rss_url: {label, added_at}} 的訂閱清單。"""
    return _load_state().get("subscriptions", {})


def add_subscription(rss_url: str, label: str) -> bool:
    """
    新增 RSS 訂閱。已存在則回傳 False（不重複加入）。
    """
    state = _load_state()
    subs = state.setdefault("subscriptions", {})
    if rss_url in subs:
        return False
    subs[rss_url] = {
        "label": label,
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_state(state)
    return True


def remove_subscription(rss_url: str) -> bool:
    """移除 RSS 訂閱，成功回傳 True。"""
    state = _load_state()
    subs = state.get("subscriptions", {})
    if rss_url not in subs:
        return False
    del subs[rss_url]
    # 同時清理該頻道的 processed 紀錄
    state.get("processed", {}).pop(rss_url, None)
    _save_state(state)
    return True


# ── 去重狀態管理 ──────────────────────────────────────────────────────────

def _make_key(rss_url: str, chat_id: str = "") -> str:
    """
    組合去重用的複合 key：rss_url|chat_id。
    chat_id 空字串代表「全域推送」（排程模式不指定特定 chat 時使用）。
    """
    return f"{rss_url}|{chat_id}" if chat_id else rss_url


def get_processed_guids(rss_url: str, chat_id: str = "") -> set[str]:
    """
    回傳 (rss_url, chat_id) 複合 key 下已處理的 GUID 集合。
    chat_id 為空時使用全域 key（排程模式）。
    """
    state = _load_state()
    key = _make_key(rss_url, chat_id)
    return set(state.get("processed", {}).get(key, []))


def mark_processed(rss_url: str, guid: str, chat_id: str = "") -> None:
    """
    標記 (rss_url, chat_id) 下的 GUID 已處理，立刻寫入磁碟。
    每個 key 最多保留最近 500 筆。
    """
    state = _load_state()
    processed = state.setdefault("processed", {})
    key = _make_key(rss_url, chat_id)
    channel_guids = processed.setdefault(key, [])
    if guid not in channel_guids:
        channel_guids.append(guid)
    processed[key] = channel_guids[-500:]
    _save_state(state)


def is_processed(rss_url: str, guid: str, chat_id: str = "") -> bool:
    """檢查 (rss_url, chat_id) 下的 GUID 是否已處理。"""
    return guid in get_processed_guids(rss_url, chat_id)


def init_empty() -> None:
    """初始化空狀態檔（首次執行時使用）。"""
    if not os.path.exists(PODCAST_STATE_FILE):
        _save_state({"subscriptions": {}, "processed": {}})
