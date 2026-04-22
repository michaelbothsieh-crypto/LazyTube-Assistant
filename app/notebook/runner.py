from __future__ import annotations

import os
import subprocess
import time


class NotebookRunner:
    def __init__(self, *, config_dir: str | None = None):
        home = os.path.expanduser("~")
        self.config_dir = config_dir or os.path.join(home, ".notebooklm-mcp-cli")

    def run(self, *args: str, verbose: bool = True, max_retries: int = 3) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["NLM_CONFIG_DIR"] = self.config_dir

        command = ["nlm", *args]
        last_result: subprocess.CompletedProcess | None = None

        for attempt in range(max_retries):
            result = subprocess.run(command, capture_output=True, text=True, env=env)
            last_result = result
            if result.returncode == 0:
                return result

            error_message = (result.stderr or result.stdout or "").lower()
            if not any(key in error_message for key in ["429", "too many requests", "timeout", "busy", "limit"]):
                break

            wait_seconds = (2**attempt) + 1
            if verbose:
                print(f"NotebookLM busy, retrying in {wait_seconds}s ({attempt + 1}/{max_retries})")
            time.sleep(wait_seconds)

        if verbose and last_result and last_result.returncode != 0:
            error = (last_result.stderr or last_result.stdout or "").strip()
            print(f"Command failed: {' '.join(command)}\n{error[:200]}")
        return last_result  # type: ignore[return-value]
