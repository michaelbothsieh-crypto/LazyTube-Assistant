import os
import httpx
import logging
import hashlib

logger = logging.getLogger(__name__)

# GitHub 配置
GH_PAT = os.environ.get("GH_PAT_WORKFLOW")
GH_OWNER = os.environ.get("GH_REPO_OWNER")
GH_REPO = os.environ.get("GH_REPO_NAME")
GH_BRANCH = os.environ.get("GH_REPO_BRANCH", "main")


def _check_gh_config() -> bool:
    """檢查 GitHub dispatch 所需的環境變數"""
    if not all([GH_PAT, GH_OWNER, GH_REPO]):
        missing = [k for k, v in {"GH_PAT_WORKFLOW": GH_PAT, "GH_REPO_OWNER": GH_OWNER, "GH_REPO_NAME": GH_REPO}.items() if not v]
        logger.error(f"GitHub dispatch 缺少環境變數: {', '.join(missing)}")
        return False
    return True


async def _dispatch(workflow_file: str, inputs: dict, timeout: float = 10.0) -> bool:
    """通用 GitHub Actions dispatch"""
    if not _check_gh_config():
        return False
    api_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/workflows/{workflow_file}/dispatches"
    payload = {"ref": GH_BRANCH, "inputs": inputs}
    headers = {"Authorization": f"Bearer {GH_PAT}", "Accept": "application/vnd.github+json"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(api_url, json=payload, headers=headers)
        if resp.status_code != 204:
            logger.error(f"dispatch {workflow_file} failed: HTTP {resp.status_code} {resp.text[:200]}")
            return False
        return True
    except Exception as e:
        logger.error(f"dispatch {workflow_file} error: {e}")
        return False


def get_hashed_id(chat_id: str) -> str:
    """將 chat_id 轉換為不具識別性的雜湊 ID (隱私保護)"""
    return hashlib.sha256(str(chat_id).encode()).hexdigest()[:12]


async def dispatch_group_workflow(chat_id: str) -> bool:
    """觸發指定群組的執行任務"""
    return await _dispatch("execute-group.yml", {"chat_id": str(chat_id)}, timeout=5.0)


async def dispatch_nlm_workflow(url: str, prompt: str = "", chat_id: str = "", message_id: str = ""):
    return await _dispatch("nlm-on-demand.yml", {
        "url": url, "prompt": prompt, "chat_id": str(chat_id), "message_id": str(message_id)
    })


async def dispatch_artifact_workflow(url: str, prompt: str = "", chat_id: str = "", message_id: str = "", slide_format: str = "pdf", slide_lang: str = "zh-TW", artifact_type: str = "slide_deck"):
    meta_prefix = f"__META:{slide_lang},{slide_format},{artifact_type}__"
    return await _dispatch("slide-on-demand.yml", {
        "url": url, "prompt": f"{meta_prefix}{prompt}", "chat_id": str(chat_id), "message_id": str(message_id)
    })


async def dispatch_batch_workflow(urls: str, prompt: str = "", chat_id: str = "", message_id: str = ""):
    """觸發批次處理工作流"""
    return await _dispatch("batch-on-demand.yml", {
        "urls": urls, "prompt": prompt, "chat_id": str(chat_id), "message_id": str(message_id)
    })


async def dispatch_research_workflow(topic: str, chat_id: str = "", message_id: str = ""):
    """觸發深度研究工作流 (Deep Research)"""
    return await _dispatch("nlm-research.yml", {
        "topic": topic, "chat_id": str(chat_id), "message_id": str(message_id)
    })


async def dispatch_update_cron_workflow() -> bool:
    """訂閱變更後觸發，自動重新計算並更新 master-scheduler 的 cron"""
    return await _dispatch("update-cron.yml", {}, timeout=5.0)
