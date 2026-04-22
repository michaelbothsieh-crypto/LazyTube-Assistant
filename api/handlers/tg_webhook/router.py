from __future__ import annotations

import logging

from api.utils.telegram import send_telegram_message

from .commands_basic import handle_help, handle_my_id, handle_start, handle_status
from .commands_dispatch import handle_batch, handle_nlm, handle_note, handle_pic, handle_research, handle_slide
from .commands_subscriptions import handle_clear, handle_list, handle_sub, handle_unsub
from .context import UpdateContext
from .validation import is_allowed_user, normalize_command_text

logger = logging.getLogger(__name__)


COMMAND_HANDLERS = {
    "/start": lambda ctx: handle_start(ctx.chat_id),
    "/my_id": lambda ctx: handle_my_id(ctx.chat_id, ctx.user_id),
    "/help": lambda ctx: handle_help(ctx.chat_id),
    "/status": lambda ctx: handle_status(ctx.chat_id),
    "/sub": lambda ctx: handle_sub(ctx.chat_id, ctx.text),
    "/unsub": lambda ctx: handle_unsub(ctx.chat_id, ctx.text),
    "/list": lambda ctx: handle_list(ctx.chat_id),
    "/clear": lambda ctx: handle_clear(ctx.chat_id),
    "/nlm": lambda ctx: handle_nlm(ctx.chat_id, ctx.text),
    "/slide": lambda ctx: handle_slide(ctx.chat_id, ctx.text),
    "/pic": lambda ctx: handle_pic(ctx.chat_id, ctx.text),
    "/note": lambda ctx: handle_note(ctx.chat_id, ctx.text),
    "/batch": lambda ctx: handle_batch(ctx.chat_id, ctx.text),
    "/research": lambda ctx: handle_research(ctx.chat_id, ctx.text),
}


async def handle_telegram_update(update: dict) -> None:
    message = update.get("message")
    if message and "new_chat_members" in message:
        for member in message["new_chat_members"]:
            if member.get("is_bot") and "lazytube" in member.get("username", "").lower():
                await handle_start(str(message["chat"]["id"]))
                return

    if not message:
        logger.info("Ignoring update without message payload")
        return

    context = UpdateContext.from_message(message, normalize_command_text(message.get("text") or ""))
    if not context.chat_id or not context.text:
        return

    if not is_allowed_user(context.user_id, context.chat_id):
        if context.text.startswith("/"):
            await send_telegram_message(
                context.chat_id,
                f"沒有權限使用此機器人。\n你的 ID：<code>{context.user_id}</code>",
            )
        return

    command = context.text.split()[0]
    handler = COMMAND_HANDLERS.get(command)
    if not handler:
        return
    await handler(context)
