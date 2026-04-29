from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import requests


ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", value.lower())


def is_valid_feed(url: str) -> bool:
    if not url:
        return False
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception:
        return False
    tag = root.tag.lower()
    if tag.endswith("rss"):
        return bool(root.findall("./channel/item"))
    if tag.endswith("feed"):
        return bool(root.findall("{http://www.w3.org/2005/Atom}entry") or root.findall("entry"))
    return False


def score_candidate(kol: dict, result: dict) -> int:
    label = normalize(kol.get("label", ""))
    host = normalize(kol.get("host", ""))
    collection = normalize(result.get("collectionName", ""))
    artist = normalize(result.get("artistName", ""))

    score = 0
    if label and label == collection:
        score += 100
    elif label and (label in collection or collection in label):
        score += 60
    if host and (host in artist or host in collection):
        score += 20
    if result.get("feedUrl"):
        score += 10
    return score


def search_feed(kol: dict, country: str) -> tuple[str, str] | None:
    source_url = kol.get("source_url", "").strip()
    if source_url:
        if is_valid_feed(source_url):
            return source_url, kol.get("label", "")
        resolved = resolve_source_url(source_url)
        if resolved and is_valid_feed(resolved):
            return resolved, kol.get("label", "")

    terms = [kol.get("label", ""), f"{kol.get('label', '')} {kol.get('host', '')}".strip()]
    best: tuple[int, str, str] | None = None

    for term in dict.fromkeys(t for t in terms if t):
        response = requests.get(
            ITUNES_SEARCH_URL,
            params={
                "term": term,
                "media": "podcast",
                "entity": "podcast",
                "country": country,
                "limit": 10,
            },
            timeout=15,
        )
        response.raise_for_status()
        for item in response.json().get("results", []):
            feed_url = item.get("feedUrl", "")
            score = score_candidate(kol, item)
            if score < 60 or not is_valid_feed(feed_url):
                continue
            label = item.get("collectionName", "")
            if best is None or score > best[0]:
                best = (score, feed_url, label)

    if best is None:
        return None
    return best[1], best[2]


def resolve_source_url(url: str) -> str | None:
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception:
        return None

    candidates = re.findall(
        r'<link[^>]+(?:type=["\']application/(?:rss|atom)\+xml["\'][^>]+href=["\']([^"\']+)["\']|href=["\']([^"\']+)["\'][^>]+type=["\']application/(?:rss|atom)\+xml["\'])',
        response.text,
        flags=re.IGNORECASE,
    )
    for first, second in candidates:
        candidate = first or second
        if candidate.startswith("//"):
            candidate = "https:" + candidate
        elif candidate.startswith("/"):
            origin = re.match(r"^https?://[^/]+", url)
            if not origin:
                continue
            candidate = origin.group(0) + candidate
        if is_valid_feed(candidate):
            return candidate
    return None


def resolve_kols(path: Path, country: str, write: bool, verbose: bool) -> int:
    kols = json.loads(path.read_text(encoding="utf-8"))
    changed = 0

    for kol in kols:
        if kol.get("rss_url"):
            continue
        result = search_feed(kol, country)
        if not result:
            if verbose:
                print(f"MISS {kol.get('kol_id')} {kol.get('label')}")
            continue

        feed_url, matched_label = result
        kol["rss_url"] = feed_url
        changed += 1
        print(f"FOUND {kol.get('kol_id')} {kol.get('label')} -> {matched_label} | {feed_url}")

    if write and changed:
        path.write_text(json.dumps(kols, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve missing website KOL RSS feeds via Apple Podcasts search.")
    parser.add_argument("--file", default="data/website_kols.json")
    parser.add_argument("--country", default="TW")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    changed = resolve_kols(Path(args.file), args.country, args.write, args.verbose)
    if changed or args.verbose:
        action = "updated" if args.write else "matched"
        print(f"{action}: {changed}")


if __name__ == "__main__":
    main()
