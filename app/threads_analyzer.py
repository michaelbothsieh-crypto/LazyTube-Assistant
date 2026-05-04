from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from html.parser import HTMLParser

import requests

from app.notebook.parsing import clean_content


THREADS_HOST_RE = re.compile(r"^https?://(?:www\.)?threads\.(?:net|com)/", re.IGNORECASE)
BOILERPLATE_RE = re.compile(
    r"^(thread|threads|instagram|meta|log in|sign up|continue with|cookie|privacy|terms|help|"
    r"open app|download app|use app|translate|likes?|reposts?|shares?|views?|followers?|following)$",
    re.IGNORECASE,
)
METRIC_RE = re.compile(
    r"^\d+(?:[,.]\d+)?\s*[kmb萬億]?\s*(likes?|replies|reposts?|shares?|views?|"
    r"則讚|則回覆|則留言|次觀看|觀看)$",
    re.IGNORECASE,
)
TIME_RE = re.compile(r"^\d+\s*(?:s|m|h|d|w|秒|分鐘|小時|天|週|周)$", re.IGNORECASE)
COUNT_TOKEN_RE = re.compile(r"^\d+(?:[,.]\d+)?\s*[kmb萬億]?$", re.IGNORECASE)
EMOJI_RE = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "]+",
    re.UNICODE,
)


@dataclass(slots=True)
class ThreadsAnalysis:
    url: str
    post_lines: list[str]
    reply_lines: list[str]
    source: str
    author: str = ""
    like_count: str = ""
    image_url: str = ""
    video_url: str = ""

    def format(self) -> str:
        post_text = "\n".join(self.post_lines).strip()
        reply_text = _summarize_replies(self.reply_lines)

        parts = [
            f"發文者：{self.author or '抓不到'}",
            f"按讚數：{self.like_count or '抓不到'}",
            "",
            "貼文主旨",
            post_text or "抓不到足夠的公開貼文文字。",
            "",
            "回覆風向",
            reply_text,
        ]
        return "\n".join(parts).strip()


def is_threads_url(url: str) -> bool:
    return bool(THREADS_HOST_RE.match((url or "").strip()))


def analyze_threads_url(url: str) -> ThreadsAnalysis:
    normalized_url = _normalize_threads_url(url)
    media = _fetch_first_media(normalized_url)
    raw_text, source = _fetch_threads_text(normalized_url)
    metadata = _extract_metadata(raw_text)
    lines = _content_lines(raw_text)
    post_lines, reply_lines = _split_post_and_replies(lines)
    return ThreadsAnalysis(
        url=normalized_url,
        post_lines=post_lines,
        reply_lines=reply_lines,
        source=source,
        author=metadata.author,
        like_count=metadata.like_count,
        image_url=media.image_url,
        video_url=media.video_url,
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


@dataclass(slots=True)
class _ThreadsMetadata:
    author: str = ""
    like_count: str = ""


def _extract_metadata(text: str) -> _ThreadsMetadata:
    lines = [_clean_line(raw_line) for raw_line in (text or "").splitlines()]
    lines = [line for line in lines if line]
    author, author_index = _extract_author(lines)
    like_count = _extract_like_count(lines, start_index=author_index + 1 if author_index >= 0 else 0)
    return _ThreadsMetadata(author=author, like_count=like_count)


def _extract_author(lines: list[str]) -> tuple[str, int]:
    thread_index = next((index for index, line in enumerate(lines) if line.lower() in {"thread", "threads"}), -1)
    search_start = thread_index + 1 if thread_index >= 0 else 0
    for index, line in enumerate(lines[search_start : search_start + 8], start=search_start):
        if METRIC_RE.fullmatch(line) or TIME_RE.fullmatch(line) or BOILERPLATE_RE.match(line):
            continue
        if _looks_like_handle(line):
            return line.lstrip("@"), index
    return "", -1


def _extract_like_count(lines: list[str], *, start_index: int) -> str:
    saw_post_text = False
    for line in lines[start_index:]:
        if TIME_RE.fullmatch(line) or BOILERPLATE_RE.match(line) or METRIC_RE.fullmatch(line):
            continue
        if _is_count_token(line):
            if saw_post_text:
                return line
            continue
        if _looks_like_handle(line):
            if saw_post_text:
                break
            continue
        saw_post_text = True
    return ""


@dataclass(slots=True)
class _ThreadsMedia:
    image_url: str = ""
    video_url: str = ""


def _fetch_first_media(url: str) -> _ThreadsMedia:
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            },
            timeout=10,
        )
        if response.status_code != 200:
            return _ThreadsMedia()
        return _extract_first_media(response.text)
    except Exception:
        return _ThreadsMedia()


def _fetch_first_image_url(url: str) -> str:
    return _fetch_first_media(url).image_url


def _extract_first_image_url(html: str) -> str:
    return _extract_first_media(html).image_url


def _extract_first_media(html: str) -> _ThreadsMedia:
    parser = _ThreadsImageMetaParser()
    parser.feed(html or "")
    return _ThreadsMedia(image_url=parser.image_url, video_url=parser.video_url)


class _ThreadsImageMetaParser(HTMLParser):
    IMAGE_META_KEYS = {
        "og:image",
        "og:image:url",
        "twitter:image",
        "twitter:image:src",
    }
    VIDEO_META_KEYS = {
        "og:video",
        "og:video:url",
        "og:video:secure_url",
        "twitter:player:stream",
    }

    def __init__(self) -> None:
        super().__init__()
        self.image_url = ""
        self.video_url = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if (self.image_url and self.video_url) or tag.lower() != "meta":
            return
        attr_map = {key.lower(): value or "" for key, value in attrs}
        meta_key = attr_map.get("property") or attr_map.get("name") or ""
        content = attr_map.get("content", "").strip()
        normalized_key = meta_key.lower()
        if not content.startswith("http"):
            return
        if not self.image_url and normalized_key in self.IMAGE_META_KEYS:
            self.image_url = content
        elif not self.video_url and normalized_key in self.VIDEO_META_KEYS:
            self.video_url = content


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
    line = EMOJI_RE.sub("", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip(" -*•\t")


def _is_noise(line: str) -> bool:
    if len(line) < 2:
        return True
    if BOILERPLATE_RE.match(line):
        return True
    if line.startswith(("Image", "Video", "Avatar", "Profile picture")):
        return True
    if METRIC_RE.fullmatch(line):
        return True
    if TIME_RE.fullmatch(line):
        return True
    if _looks_like_handle(line):
        return True
    return False


def _is_count_token(line: str) -> bool:
    return bool(COUNT_TOKEN_RE.fullmatch(line))


def _looks_like_handle(line: str) -> bool:
    if re.search(r"[\u4e00-\u9fff\s]", line):
        return False
    return bool(re.fullmatch(r"@?[A-Za-z0-9_.]{2,30}", line))


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

    samples = "\n".join(f"- {line}" for line in reply_lines[:4])
    return f"整體風向：{tone}\n代表回覆：\n{samples}"
