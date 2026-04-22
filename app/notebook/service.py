from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from api.utils.prompt_manager import get_nlm_prompt

from .notebook_session import NotebookSession
from .parsing import extract_existing_path, parse_query_output
from .runner import NotebookRunner
from .source_loader import SourceLoader


class NotebookService:
    def __init__(self):
        self.runner = NotebookRunner()
        self.sources = SourceLoader(self.runner)

    def run_nlm(self, *args: str, verbose: bool = True, max_retries: int = 3):
        return self.runner.run(*args, verbose=verbose, max_retries=max_retries)

    def process_video(self, url: str, title: str, custom_prompt: str | None = None) -> str:
        with NotebookSession(self.runner, "YT") as session:
            if not session.ready():
                return "❌ 無法建立 NotebookLM notebook。"
            if not self.sources.add_source(session.notebook_id, url, wait=True):
                return "❌ 無法加入影片來源。"

            prompt = get_nlm_prompt(custom_prompt)
            result = self.runner.run("query", "notebook", session.notebook_id, prompt)
            if result.returncode != 0:
                return "❌ 摘要生成失敗。"
            return parse_query_output(result.stdout)

    def process_batch(self, urls: list[str], custom_prompt: str | None = None) -> str:
        with NotebookSession(self.runner, "BATCH") as session:
            if not session.ready():
                return "❌ 無法建立 NotebookLM notebook。"

            with ThreadPoolExecutor(max_workers=5) as executor:
                list(executor.map(lambda value: self.sources.add_source(session.notebook_id, value.strip(), wait=False), urls))

            time.sleep(5)
            prompt = f"{get_nlm_prompt(custom_prompt)}\n\n請比較所有來源，整理共同重點與差異。"
            result = self.runner.run("query", "notebook", session.notebook_id, prompt)
            if result.returncode != 0:
                return "❌ 批次摘要生成失敗。"
            return parse_query_output(result.stdout)

    def process_artifact(
        self,
        url: str,
        title: str,
        artifact_type: str = "slide_deck",
        custom_prompt: str | None = None,
        **kwargs,
    ) -> str:
        slide_lang = kwargs.get("slide_lang") or kwargs.get("language") or "zh-TW"
        with NotebookSession(self.runner, "ART") as session:
            if not session.ready() or not self.sources.add_source(session.notebook_id, url, wait=True):
                return "❌ 無法建立 artifact 來源。"

            command = ["slides", "create", session.notebook_id, "--language", slide_lang, "--confirm"]
            if artifact_type == "infographic":
                command = ["infographic", "create", session.notebook_id, "--language", slide_lang, "--confirm"]
            elif artifact_type == "report":
                command = ["report", "create", session.notebook_id, "--language", slide_lang, "--confirm"]

            if custom_prompt:
                command.extend(["--focus", get_nlm_prompt(custom_prompt)])

            result = self.runner.run(*command)
            if result.returncode != 0:
                return "❌ Artifact 生成失敗。"

            existing_path = extract_existing_path(result.stdout)
            if existing_path:
                return existing_path

            output = parse_query_output(result.stdout)
            return output or result.stdout.strip() or "✅ Artifact 任務已完成。"

    async def research_topic(self, topic: str, mode: str = "fast") -> tuple[bool, str]:
        with NotebookSession(self.runner, "RES") as session:
            if not session.ready():
                return False, "無法建立 NotebookLM notebook。"

            if self.runner.run("research", "start", "--notebook-id", session.notebook_id, "--mode", mode, topic).returncode != 0:
                return False, "研究任務啟動失敗。"

            interval = 30 if mode == "deep" else 15
            timeout = 1200 if mode == "deep" else 600
            started = time.time()
            while time.time() - started < timeout:
                status_result = self.runner.run("research", "status", session.notebook_id, "--max-wait", "0", verbose=False)
                status_text = status_result.stdout.strip().lower()
                if any(flag in status_text for flag in ["completed", "success", "no active research", "ready to import"]):
                    break
                time.sleep(interval)

            self.runner.run("research", "import", session.notebook_id, verbose=False)
            prompt = (
                f"請根據研究主題「{topic}」整理完整報告，包含核心結論、依據、風險與建議，"
                "最後補一段可直接傳給使用者的摘要。"
            )
            result = self.runner.run("query", "notebook", session.notebook_id, prompt)
            if result.returncode != 0:
                return False, "研究報告生成失敗。"
            return True, parse_query_output(result.stdout)


NotebookManager = NotebookService
