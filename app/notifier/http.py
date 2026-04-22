from __future__ import annotations

import requests


def post_json(url: str, *, payload: dict | list, headers: dict | None = None, timeout: int = 15) -> requests.Response:
    return requests.post(url, json=payload, headers=headers, timeout=timeout)
