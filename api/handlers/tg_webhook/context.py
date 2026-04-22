from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UpdateContext:
    chat_id: str
    user_id: str
    text: str

    @classmethod
    def from_message(cls, message: dict, normalized_text: str) -> UpdateContext:
        return cls(
            chat_id=str(message.get("chat", {}).get("id", "")),
            user_id=str(message.get("from", {}).get("id", "")),
            text=normalized_text,
        )
