from __future__ import annotations

import json
import os
import re


def extract_notebook_id(output: str, fallback: str) -> str:
    match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", output or "")
    return match.group(1) if match else fallback


def clean_content(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"Cookie Policy|Terms of Service|Privacy Policy|Copyright", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


def strip_numeric_citations(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s*\[\d+(?:\s*(?:[,，\-–]\s*)\d+)*\]", "", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def parse_query_output(raw: str) -> str:
    output = (raw or "").strip()
    try:
        data = json.loads(output)
        if isinstance(data, dict):
            output = data.get("value", {}).get("answer", data.get("answer", output))
    except Exception:
        pass

    output = re.sub(
        r"\*\*(Thinking|Thought|Summarizing|Analysis|Defining|Finalizing).*?\*\*[\s\n]*",
        "",
        output,
        flags=re.IGNORECASE,
    ).strip()
    return strip_numeric_citations(output)


def extract_existing_path(raw: str) -> str:
    for candidate in re.findall(r"([A-Za-z]:\\[^\s]+|/tmp/[^\s]+)", raw or ""):
        normalized = candidate.strip().strip('"').strip("'")
        if os.path.exists(normalized):
            return normalized
    return ""
