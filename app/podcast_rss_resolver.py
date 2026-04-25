"""
app/podcast_rss_resolver.py — 從任意 URL 自動解析出 Podcast RSS Feed。

支援策略（依序嘗試）：
  1. URL 本身就是 RSS（含 .xml / feeds. / rss 等特徵）
  2. HTML <link rel="alternate" type="application/rss+xml"> 自動發現
  3. 常見 Podcast 平台 URL 解析（SoundOn / Spotify / Apple Podcasts / Firstory）
  4. 讀取 HTML 頁面搜尋 RSS 連結
"""
from __future__ import annotations

import re

import feedparser
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PodcastBot/1.0; +https://github.com/lazytube)"
    )
}
TIMEOUT = 15


def resolve_rss(url: str) -> tuple[str | None, str]:
    """
    嘗試從 url 解析 RSS feed URL 與頻道名稱。
    回傳 (rss_url, label)，失敗時 rss_url 為 None。
    """
    url = url.strip().rstrip("/")

    # 策略 1：URL 看起來就像 RSS
    if _looks_like_rss(url):
        label = _probe_feed_label(url)
        if label:
            return url, label

    # 策略 2：SoundOn
    m = re.search(r"soundon\.fm/podcasts/([0-9a-f-]+)", url)
    if m:
        rss = f"https://feeds.soundon.fm/podcasts/{m.group(1)}.xml"
        label = _probe_feed_label(rss)
        return (rss, label) if label else (None, "")

    # 策略 3：Firstory
    m = re.search(r"firstory\.me/user/([^/?#]+)", url)
    if m:
        rss = f"https://open.firstory.me/rss/user/{m.group(1)}"
        label = _probe_feed_label(rss)
        return (rss, label) if label else (None, "")

    # 策略 4：Apple Podcasts
    m = re.search(r"podcasts\.apple\.com/.+/id(\d+)", url)
    if m:
        rss = _resolve_apple_rss(m.group(1))
        if rss:
            label = _probe_feed_label(rss)
            return (rss, label or "Apple Podcast")

    # 策略 5：HTML auto-discovery
    rss = _discover_from_html(url)
    if rss:
        label = _probe_feed_label(rss)
        return (rss, label) if label else (rss, _domain_label(url))

    return None, ""


def _looks_like_rss(url: str) -> bool:
    """URL 特徵判斷是否為 RSS。"""
    markers = [".xml", "/rss", "/feed", "feeds.", "rss2", "podcast.xml"]
    return any(m in url.lower() for m in markers)


def _probe_feed_label(rss_url: str) -> str:
    """嘗試解析 RSS 取得頻道標題。失敗回傳空字串。"""
    try:
        feed = feedparser.parse(rss_url)
        title = feed.feed.get("title", "").strip()
        return title if title else ""
    except Exception:
        return ""


def _domain_label(url: str) -> str:
    """從 URL 萃取簡短 domain 作為 fallback label。"""
    m = re.search(r"https?://([^/]+)", url)
    return m.group(1) if m else url[:30]


def _discover_from_html(url: str) -> str | None:
    """在 HTML 頁面中搜尋 <link type="application/rss+xml"> 標籤。"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        html = resp.text
        # <link> auto-discovery
        m = re.search(
            r'<link[^>]+type=["\']application/rss\+xml["\'][^>]+href=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if m:
            href = m.group(1)
            if href.startswith("http"):
                return href
            # 相對路徑補全
            base = re.match(r"(https?://[^/]+)", url)
            return (base.group(1) + href) if base else None
        return None
    except Exception:
        return None


def _resolve_apple_rss(podcast_id: str) -> str | None:
    """透過 Apple iTunes lookup API 取得 RSS URL。"""
    try:
        resp = requests.get(
            f"https://itunes.apple.com/lookup?id={podcast_id}&entity=podcast",
            timeout=TIMEOUT,
        )
        data = resp.json()
        results = data.get("results", [])
        if results:
            return results[0].get("feedUrl")
        return None
    except Exception:
        return None
