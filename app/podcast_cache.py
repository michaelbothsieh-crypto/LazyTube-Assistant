from __future__ import annotations

import hashlib
import json
from typing import Optional

import requests

from app.config import Config


def _is_enabled() -> bool:
    return bool(Config.REDIS_URL and Config.REDIS_TOKEN)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {Config.REDIS_TOKEN}"}


def build_analysis_cache_key(rss_url: str, guid: str, prompt_key: str) -> str:
    digest = hashlib.sha256(f"{rss_url}|{guid}|{prompt_key}".encode("utf-8")).hexdigest()[:16]
    return f"podcast:analysis:{digest}"


def get_cached_analysis(rss_url: str, guid: str, prompt_key: str) -> Optional[str]:
    if not _is_enabled():
        return None
    key = build_analysis_cache_key(rss_url, guid, prompt_key)
    try:
        response = requests.post(
            Config.REDIS_URL,
            json=["GET", key],
            headers=_headers(),
            timeout=10,
        )
        if response.status_code != 200:
            return None
        payload = response.json().get("result")
        if not payload:
            return None
        data = json.loads(payload)
        analysis = data.get("analysis")
        return analysis if isinstance(analysis, str) and analysis.strip() else None
    except Exception:
        return None


def set_cached_analysis(rss_url: str, guid: str, prompt_key: str, analysis: str) -> bool:
    if not _is_enabled() or not analysis.strip():
        return False
    key = build_analysis_cache_key(rss_url, guid, prompt_key)
    payload = json.dumps({"analysis": analysis}, ensure_ascii=False)
    try:
        response = requests.post(
            Config.REDIS_URL,
            json=["SET", key, payload, "EX", str(Config.REDIS_PODCAST_TTL)],
            headers=_headers(),
            timeout=10,
        )
        return response.status_code == 200
    except Exception:
        return False
