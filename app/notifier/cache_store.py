from __future__ import annotations

import base64
import uuid
from typing import Optional

from app.config import Config

from .http import post_json


def cache_file(file_path: str, *, prefix: str, ttl_seconds: int, route: str) -> Optional[str]:
    try:
        with open(file_path, "rb") as file_handle:
            payload = base64.b64encode(file_handle.read()).decode("utf-8")
    except Exception:
        return None

    return cache_content(payload, prefix=prefix, ttl_seconds=ttl_seconds, route=route)


def cache_text(content: str, *, prefix: str, ttl_seconds: int, route: str) -> Optional[str]:
    payload = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    return cache_content(payload, prefix=prefix, ttl_seconds=ttl_seconds, route=route)


def cache_content(payload: str, *, prefix: str, ttl_seconds: int, route: str) -> Optional[str]:
    if not Config.REDIS_URL or not Config.REDIS_TOKEN:
        return None

    cache_id = uuid.uuid4().hex[:8]
    redis_key = f"{prefix}_{cache_id}"
    headers = {"Authorization": f"Bearer {Config.REDIS_TOKEN}"}

    try:
        response = post_json(
            Config.REDIS_URL,
            payload=["SET", redis_key, payload, "EX", str(ttl_seconds)],
            headers=headers,
            timeout=20,
        )
        if response.status_code != 200:
            return None
    except Exception:
        return None

    base_url = Config.APP_BASE_URL.rstrip("/")
    return f"{base_url}{route}?id={cache_id}"
