from __future__ import annotations


def extract_message_id(response: dict | None) -> str:
    """從 Telegram sendMessage 回應中提取 message_id。"""
    if not response or not response.get("ok"):
        return ""
    return str(response.get("result", {}).get("message_id", ""))
