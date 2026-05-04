from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

import requests

from app.notebook.parsing import clean_content


THREADS_HOST_RE = re.compile(r"^https?://(?:www\.)?threads\.(?:net|com)/", re.IGNORECASE)
BOILERPLATE_RE = re.compile(
    r"^(threads|instagram|meta|log in|sign up|continue with|cookie|privacy|terms|help|"
    r"open app|download app|use app|likes?|reposts?|shares?|views?|followers?|following)$",
    re.IGNORECASE,
)


@dataclass(slots=True)
class ThreadsAnalysis:
    url: str
    post_lines: list[str]
    reply_lines: list[str]
    source: str

    def format(self) -> str:
        post_text = "\n".join(self.post_lines).strip()
        reply_text = _summarize_replies(self.reply_lines)

        parts = [
            "⚡ Threads 極速解析",
            f"🔗 {self.url}",
            "",
            "🧵 貼文主旨",
            post_text or "抓不到足夠的公開貼文文字。",
            "",
            "💬 回覆/留言風向",
            reply_text,
        ]
        if self.source:
            parts.extend(["", f"來源：{self.source}"])
        return "\n".join(parts).strip()


def is_threads_url(url: str) -> bool:
    return bool(THREADS_HOST_RE.match((url or "").strip()))


def analyze_threads_url(url: str) -> ThreadsAnalysis:
    normalized_url = _normalize_threads_url(url)
    raw_text, source = _fetch_threads_text(normalized_url)
    lines = _content_lines(raw_text)
    post_lines, reply_lines = _split_post_and_replies(lines)
    return ThreadsAnalysis(
        url=normalized_url,
        post_lines=post_lines,
        reply_lines=reply_lines,
        source=source,
    )


def _normalize_threads_url(url: str) -> str:
    cleaned = (url or "").strip()
    if not is_threads_url(cleaned):
        raise ValueError("請提供 Threads 貼文 URL。")
    return cleaned.split("#", 1)[0]


def _fetch_threads_text(url: str) -> tuple[str, str]:
    encoded_url = urllib.parse.quote(url, safe="")
    worker_text = _fetch_worker_text(encoded_url)
    if worker_text:
        return worker_text, "worker"

    jina_text = _fetch_jina_text(encoded_url)
    if jina_text:
        return jina_text, "jina"

    return "", ""


def _fetch_worker_text(encoded_url: str) -> str:
    try:
        response = requests.get(
            f"https://lazypipe-worker.hsieh130.workers.dev/?url={encoded_url}",
            timeout=20,
        )
        if response.status_code != 200:
            return ""
        payload = response.json()
        if not payload.get("success"):
            return ""
        return clean_content(str(payload.get("content") or ""))
    except Exception:
        return ""


def _fetch_jina_text(encoded_url: str) -> str:
    try:
        response = requests.get(f"https://r.jina.ai/{encoded_url}", timeout=20)
        if response.status_code != 200:
            return ""
        return clean_content(response.text)
    except Exception:
        return ""


def _content_lines(text: str) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in (text or "").splitlines():
        line = _clean_line(raw_line)
        if not line or line in seen:
            continue
        if _is_noise(line):
            continue
        seen.add(line)
        lines.append(line)
    return lines


def _clean_line(line: str) -> str:
    line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
    line = re.sub(r"https?://\S+", "", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip(" -*•\t")


def _is_noise(line: str) -> bool:
    if len(line) < 2:
        return True
    if BOILERPLATE_RE.match(line):
        return True
    if line.startswith(("Image", "Video", "Avatar", "Profile picture")):
        return True
    if re.fullmatch(r"[\d,]+\s*(likes?|replies|reposts?|views?)", line, re.IGNORECASE):
        return True
    return False


def _split_post_and_replies(lines: list[str]) -> tuple[list[str], list[str]]:
    if not lines:
        return [], []

    reply_markers = {"reply", "replies", "replied", "回覆", "留言"}
    marker_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.lower() in reply_markers or line.lower().startswith("replies")
        ),
        -1,
    )
    if marker_index > 0:
        post_candidates = lines[:marker_index]
        reply_candidates = lines[marker_index + 1 :]
    else:
        post_candidates = lines[: min(5, len(lines))]
        reply_candidates = lines[min(5, len(lines)) :]

    post_lines = _trim_lines(post_candidates, max_lines=5, max_chars=700)
    reply_lines = _trim_lines(reply_candidates, max_lines=8, max_chars=900)
    return post_lines, reply_lines


def _trim_lines(lines: list[str], *, max_lines: int, max_chars: int) -> list[str]:
    selected: list[str] = []
    total = 0
    for line in lines:
        if len(selected) >= max_lines:
            break
        if total + len(line) > max_chars:
            break
        selected.append(line)
        total += len(line)
    return selected


def _summarize_replies(reply_lines: list[str]) -> str:
    if not reply_lines:
        return "公開頁面沒有抓到足夠回覆，可能需要登入或貼文本身回覆很少。"

    question_count = sum(1 for line in reply_lines if "?" in line or "？" in line)
    positive_count = sum(1 for line in reply_lines if re.search(r"同意|讚|好|支持|agree|yes|true", line, re.IGNORECASE))
    skeptical_count = sum(1 for line in reply_lines if re.search(r"但|可是|不|疑|錯|假|however|but|no|fake", line, re.IGNORECASE))

    tone = "偏討論/補充"
    if positive_count > skeptical_count and positive_count >= question_count:
        tone = "偏認同"
    elif skeptical_count > positive_count and skeptical_count >= question_count:
        tone = "偏質疑/反駁"
    elif question_count:
        tone = "偏提問"

    samples = "\n".join(f"・{line}" for line in reply_lines[:4])
    return f"整體風向：{tone}\n代表回覆：\n{samples}"
