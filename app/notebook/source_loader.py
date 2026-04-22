from __future__ import annotations

import os
import tempfile
import urllib.parse

import requests

from .parsing import clean_content
from .runner import NotebookRunner


class SourceLoader:
    def __init__(self, runner: NotebookRunner):
        self.runner = runner

    def add_source(self, notebook_id: str, url: str, *, wait: bool = True) -> bool:
        wait_flag = ["--wait"] if wait else []
        if "youtube.com" in url or "youtu.be" in url:
            response = self.runner.run("source", "add", notebook_id, "--url", url, *wait_flag)
            if response.returncode == 0:
                return True

        decoded_url = urllib.parse.unquote(url)
        encoded_url = urllib.parse.quote(decoded_url, safe="")

        if self.runner.run("source", "add", notebook_id, "--url", f"https://r.jina.ai/{encoded_url}", *wait_flag).returncode == 0:
            return True

        worker_content = self._fetch_worker_content(encoded_url)
        if worker_content and self._add_text_file(notebook_id, worker_content, wait=wait):
            return True

        firecrawl_content = self._fetch_firecrawl_content(decoded_url)
        if firecrawl_content and self._add_text_file(notebook_id, firecrawl_content, wait=wait):
            return True

        return False

    def _add_text_file(self, notebook_id: str, content: str, *, wait: bool) -> bool:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        wait_flag = ["--wait"] if wait else []
        try:
            result = self.runner.run("source", "add", notebook_id, "--file", temp_path, *wait_flag)
            return result.returncode == 0
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def _fetch_worker_content(self, encoded_url: str) -> str:
        try:
            response = requests.get(
                f"https://lazypipe-worker.hsieh130.workers.dev/?url={encoded_url}",
                timeout=40,
            )
            if response.status_code != 200:
                return ""
            payload = response.json()
            if not payload.get("success"):
                return ""
            content = clean_content(payload.get("content", ""))
            return content if len(content) > 100 else ""
        except Exception:
            return ""

    def _fetch_firecrawl_content(self, decoded_url: str) -> str:
        firecrawl_key = os.environ.get("FIRECRAWL_API_KEY")
        if not firecrawl_key:
            return ""

        try:
            response = requests.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={
                    "Authorization": f"Bearer {firecrawl_key}",
                    "Content-Type": "application/json",
                },
                json={"url": decoded_url, "formats": ["markdown"], "onlyMainContent": True},
                timeout=30,
            )
            if response.status_code != 200:
                return ""
            return response.json().get("data", {}).get("markdown", "")
        except Exception:
            return ""
