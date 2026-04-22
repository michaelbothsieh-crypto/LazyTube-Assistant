from __future__ import annotations

import re
from dataclasses import dataclass

from api.utils.prompt_manager import get_nlm_prompt, get_optimized_prompt
from app.config import Config


@dataclass(slots=True)
class SlideRequest:
    url: str
    prompt: str
    language: str
    file_format: str


def extract_url_and_prompt(text: str) -> tuple[str | None, str]:
    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        return None, ""
    prompt = get_nlm_prompt(parts[2] if len(parts) >= 3 else "")
    return parts[1], prompt[:Config.MAX_PROMPT_LENGTH]


def parse_slide_request(text: str) -> SlideRequest | None:
    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        return None

    url = parts[1]
    remainder = parts[2] if len(parts) >= 3 else ""
    prompt = get_optimized_prompt(url)
    language = "zh-TW"
    file_format = "pdf"

    if remainder:
        tokens = remainder.split()
        if tokens and tokens[-1].lower() in {"pdf", "pptx"}:
            file_format = tokens.pop().lower()
        if tokens and _looks_like_language(tokens[-1]):
            language = tokens.pop()
        if tokens and " ".join(tokens).strip() != "_":
            prompt = " ".join(tokens).strip()

    return SlideRequest(
        url=url,
        prompt=prompt[:Config.MAX_PROMPT_LENGTH],
        language=language,
        file_format=file_format,
    )


def parse_batch_request(text: str) -> tuple[list[str], str]:
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return [], ""

    content = parts[1]
    urls = re.findall(r"https?://[^\s,()]+", content)[:Config.MAX_BATCH_URLS]
    prompt_source = content
    for url in urls:
        prompt_source = prompt_source.replace(url, "")
    prompt_source = re.sub(r"^[,\s]+", "", prompt_source).strip()
    return urls, get_nlm_prompt(prompt_source)[:Config.MAX_PROMPT_LENGTH]


def parse_research_request(text: str) -> tuple[str | None, str]:
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None, "fast"

    content = parts[1].strip()
    words = content.split()
    if len(words) > 1 and words[-1].lower() in {"fast", "deep"}:
        return " ".join(words[:-1]).strip(), words[-1].lower()
    return content, "fast"


def parse_subscription_request(text: str) -> tuple[str | None, str, str]:
    parts = text.split()
    if len(parts) < 2:
        return None, "", ""

    url = parts[1]
    prompt = ""
    preferred_time = ""
    if len(parts) >= 3:
        last_part = parts[-1]
        time_match = re.match(r"^(\d{1,2})(?::\d{2})?(?::\d{2})?$", last_part)
        if time_match:
            from app.subscription_vm import SubscriptionViewModel

            hour = int(time_match.group(1))
            if 0 <= hour <= 23:
                preferred_time = SubscriptionViewModel.snap_preferred_time(hour)
                prompt = get_nlm_prompt(" ".join(parts[2:-1])) if len(parts) > 3 else ""
            else:
                return url, "__INVALID_TIME__", ""
        else:
            prompt = get_nlm_prompt(" ".join(parts[2:]))

    return url, prompt[:Config.MAX_PROMPT_LENGTH], preferred_time


def _looks_like_language(value: str) -> bool:
    return (len(value) == 2 and value.isalpha()) or ("-" in value and len(value) <= 6)
