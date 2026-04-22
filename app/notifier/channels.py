LINE_PREFIXES = ("U", "C", "R")


def is_line_chat(chat_id: str | None) -> bool:
    return str(chat_id or "").startswith(LINE_PREFIXES)
