import hashlib
import logging

import httpx

from app.config import Config

logger = logging.getLogger(__name__)


def get_hashed_id(chat_id: str) -> str:
    """將 chat_id 轉換為不具識別性的雜湊 ID（隱私保護）。"""
    return hashlib.sha256(str(chat_id).encode()).hexdigest()[:12]


class GitHubActionManager:
    """GitHub Actions workflow_dispatch 的統一介面。"""

    @staticmethod
    def _is_configured() -> bool:
        missing = [k for k, v in {
            "GH_PAT_WORKFLOW": Config.GH_PAT_WORKFLOW,
            "GH_REPO_OWNER": Config.GH_REPO_OWNER,
            "GH_REPO_NAME": Config.GH_REPO_NAME,
        }.items() if not v]
        if missing:
            logger.error("GitHub dispatch 缺少環境變數: %s", ", ".join(missing))
            return False
        return True

    @staticmethod
    async def dispatch(workflow_file: str, inputs: dict, timeout: float = 10.0) -> bool:
        """觸發指定的 GitHub Actions workflow。"""
        if not GitHubActionManager._is_configured():
            return False
        api_url = (
            f"https://api.github.com/repos/{Config.GH_REPO_OWNER}/{Config.GH_REPO_NAME}"
            f"/actions/workflows/{workflow_file}/dispatches"
        )
        payload = {"ref": Config.GH_REPO_BRANCH, "inputs": inputs}
        headers = {"Authorization": f"Bearer {Config.GH_PAT_WORKFLOW}", "Accept": "application/vnd.github+json"}
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(api_url, json=payload, headers=headers)
            if resp.status_code != 204:
                logger.error("dispatch %s failed: HTTP %s %s", workflow_file, resp.status_code, resp.text[:200])
                return False
            return True
        except Exception as e:
            logger.error("dispatch %s error: %s", workflow_file, e)
            return False

    @staticmethod
    async def trigger_group(chat_id: str) -> bool:
        """觸發指定群組的執行任務。"""
        return await GitHubActionManager.dispatch(
            "execute-group.yml", {"chat_id": str(chat_id)}, timeout=5.0
        )

    @staticmethod
    async def trigger_nlm(url: str, prompt: str = "", chat_id: str = "", message_id: str = "") -> bool:
        return await GitHubActionManager.dispatch("nlm-on-demand.yml", {
            "url": url, "prompt": prompt, "chat_id": str(chat_id), "message_id": str(message_id)
        })

    @staticmethod
    async def trigger_artifact(
        url: str,
        prompt: str = "",
        chat_id: str = "",
        message_id: str = "",
        slide_format: str = "pdf",
        slide_lang: str = "zh-TW",
        artifact_type: str = "slide_deck",
    ) -> bool:
        meta_prefix = f"__META:{slide_lang},{slide_format},{artifact_type}__"
        return await GitHubActionManager.dispatch("slide-on-demand.yml", {
            "url": url, "prompt": f"{meta_prefix}{prompt}", "chat_id": str(chat_id), "message_id": str(message_id)
        })

    @staticmethod
    async def trigger_batch(urls: str, prompt: str = "", chat_id: str = "", message_id: str = "") -> bool:
        """觸發批次處理工作流。"""
        return await GitHubActionManager.dispatch("batch-on-demand.yml", {
            "urls": urls, "prompt": prompt, "chat_id": str(chat_id), "message_id": str(message_id)
        })

    @staticmethod
    async def trigger_research(topic: str, mode: str = "fast", chat_id: str = "", message_id: str = "") -> bool:
        """觸發深度研究工作流（Deep Research）。"""
        inputs = {"topic": topic, "chat_id": str(chat_id), "message_id": str(message_id)}
        if mode == "deep":
            inputs["mode"] = "deep"
        return await GitHubActionManager.dispatch("nlm-research.yml", inputs)

    @staticmethod
    async def trigger_update_cron() -> bool:
        """訂閱變更後觸發，自動重新計算並更新 master-scheduler 的 cron。"""
        return await GitHubActionManager.dispatch("update-cron.yml", {}, timeout=5.0)


# 模組層級 shim，保持向後相容
async def dispatch_group_workflow(chat_id: str) -> bool:
    return await GitHubActionManager.trigger_group(chat_id)

async def dispatch_nlm_workflow(url: str, prompt: str = "", chat_id: str = "", message_id: str = "") -> bool:
    return await GitHubActionManager.trigger_nlm(url, prompt, chat_id, message_id)

async def dispatch_artifact_workflow(url: str, prompt: str = "", chat_id: str = "", message_id: str = "", slide_format: str = "pdf", slide_lang: str = "zh-TW", artifact_type: str = "slide_deck") -> bool:
    return await GitHubActionManager.trigger_artifact(url, prompt, chat_id, message_id, slide_format, slide_lang, artifact_type)

async def dispatch_batch_workflow(urls: str, prompt: str = "", chat_id: str = "", message_id: str = "") -> bool:
    return await GitHubActionManager.trigger_batch(urls, prompt, chat_id, message_id)

async def dispatch_research_workflow(topic: str, mode: str = "fast", chat_id: str = "", message_id: str = "") -> bool:
    return await GitHubActionManager.trigger_research(topic, mode, chat_id, message_id)

async def dispatch_update_cron_workflow() -> bool:
    return await GitHubActionManager.trigger_update_cron()
