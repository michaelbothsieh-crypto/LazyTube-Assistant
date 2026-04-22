from __future__ import annotations

import base64
import uuid
from typing import Optional

from .http import post_json


class CacheStore:
    def __init__(self, redis_url: str, redis_token: str, base_url: str) -> None:
        self._redis_url = redis_url
        self._redis_token = redis_token
        self._base_url = base_url.rstrip("/")

    def cache_file(self, file_path: str, *, prefix: str, ttl_seconds: int, route: str) -> Optional[str]:
        try:
            with open(file_path, "rb") as file_handle:
                payload = base64.b64encode(file_handle.read()).decode("utf-8")
        except Exception:
            return None
        return self._cache_content(payload, prefix=prefix, ttl_seconds=ttl_seconds, route=route)

    def cache_text(self, content: str, *, prefix: str, ttl_seconds: int, route: str) -> Optional[str]:
        payload = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        return self._cache_content(payload, prefix=prefix, ttl_seconds=ttl_seconds, route=route)

    def _cache_content(self, payload: str, *, prefix: str, ttl_seconds: int, route: str) -> Optional[str]:
        cache_id = uuid.uuid4().hex[:8]
        redis_key = f"{prefix}_{cache_id}"
        headers = {"Authorization": f"Bearer {self._redis_token}"}
        try:
            response = post_json(
                self._redis_url,
                payload=["SET", redis_key, payload, "EX", str(ttl_seconds)],
                headers=headers,
                timeout=20,
            )
            if response.status_code != 200:
                return None
        except Exception:
            return None
        return f"{self._base_url}{route}?id={cache_id}"
