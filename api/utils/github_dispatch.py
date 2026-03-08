import os
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# GitHub 配置
GH_PAT = os.environ.get("GH_PAT_WORKFLOW")
GH_OWNER = os.environ.get("GH_REPO_OWNER")
GH_REPO = os.environ.get("GH_REPO_NAME")
GH_BRANCH = os.environ.get("GH_REPO_BRANCH", "main")

async def dispatch_nlm_workflow(url: str, prompt: str = "", chat_id: str = "", message_id: str = ""):
    """
    /// 觸發 GitHub Actions 的 YT Summary 工作流
    """
    if not all([GH_PAT, GH_OWNER, GH_REPO]):
        logger.error("缺少 GitHub 環境變數：GH_PAT_WORKFLOW, GH_REPO_OWNER, GH_REPO_NAME")
        return False

    workflow_file = "nlm-on-demand.yml"
    api_url = (f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/workflows/{workflow_file}/dispatches")
    payload = {"ref": GH_BRANCH, "inputs": {"url": url, "prompt": prompt, "chat_id": str(chat_id), "message_id": str(message_id)}}
    headers = {"Authorization": f"Bearer {GH_PAT}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)
        
        if response.status_code != 204:
            logger.error(f"GitHub API 錯誤 ({response.status_code}): {response.text[:200]}")
            return False
        return True
    except Exception as e:
        logger.error(f"GitHub API 請求異常: {e}")
        return False

async def dispatch_artifact_workflow(url: str, prompt: str = "", chat_id: str = "", message_id: str = "", slide_format: str = "pdf", slide_lang: str = "zh-TW", artifact_type: str = "slide_deck"):
    """
    /// 觸發 GitHub Actions slide-on-demand.yml (通用版)
    /// artifact_type: 'slide_deck', 'infographic', 'report'
    """
    if not all([GH_PAT, GH_OWNER, GH_REPO]): return False

    slide_workflow_file = "slide-on-demand.yml"
    api_url = (f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/workflows/{slide_workflow_file}/dispatches")
    
    # 元數據格式: __META:lang,format,type__真實Prompt
    meta_prefix = f"__META:{slide_lang},{slide_format},{artifact_type}__"
    effective_prompt = f"{meta_prefix}{prompt}"

    payload = {"ref": GH_BRANCH, "inputs": {"url": url, "prompt": effective_prompt, "chat_id": str(chat_id), "message_id": str(message_id)}}
    headers = {"Authorization": f"Bearer {GH_PAT}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)
        return response.status_code == 204
    except Exception as e:
        logger.error(f"GitHub API 請求異常: {e}")
        return False
