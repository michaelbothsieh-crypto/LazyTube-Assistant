from __future__ import annotations

from typing import TypedDict


class TgUser(TypedDict, total=False):
    id: int
    is_bot: bool
    username: str
    first_name: str


class TgChat(TypedDict, total=False):
    id: int
    type: str
    title: str


class TgMessage(TypedDict, total=False):
    message_id: int
    from_: TgUser
    chat: TgChat
    text: str
    new_chat_members: list[TgUser]


class TgUpdate(TypedDict, total=False):
    update_id: int
    message: TgMessage
