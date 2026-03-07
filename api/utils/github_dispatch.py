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
    回傳 True 表示觸發成功（204 No Content）
    """
    if not all([GH_PAT, GH_OWNER, GH_REPO]):
        logger.error("缺少 GitHub 環境變數：GH_PAT_WORKFLOW, GH_REPO_OWNER, GH_REPO_NAME")
        return False

    workflow_file = "yt-summary.yml"
    api_url = (
        f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}"
        f"/actions/workflows/{workflow_file}/dispatches"
    )

    payload = {
        "ref": GH_BRANCH,
        "inputs": {
            "url": url,
            "prompt": prompt,
            "chat_id": str(chat_id),
            "message_id": str(message_id)
        }
    }

    headers = {
        "Authorization": f"Bearer {GH_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)

        if response.status_code == 204:
            logger.info(f"✅ GitHub Actions 觸發成功：{url[:60]}")
            return True
        else:
            logger.error(
                f"❌ GitHub Actions 觸發失敗：{response.status_code} - {response.text}"
            )
            return False

    except httpx.TimeoutException:
        logger.error("GitHub API 請求逾時")
        return False
    except Exception as e:
        logger.error(f"GitHub API 請求異常: {e}")
        return False

async def dispatch_slide_workflow(url: str, prompt: str = "", chat_id: str = "", message_id: str = "", slide_format: str = "pdf"):
    """
    /// 觸發 GitHub Actions slide-on-demand.yml
    回傳 True 表示觸發成功（204 No Content）
    """
    if not all([GH_PAT, GH_OWNER, GH_REPO]):
        logger.error("缺少 GitHub 環境變數：GH_PAT_WORKFLOW, GH_REPO_OWNER, GH_REPO_NAME")
        return False

    slide_workflow_file = "slide-on-demand.yml"
    api_url = (
        f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}"
        f"/actions/workflows/{slide_workflow_file}/dispatches"
    )

    # 由於無法修改 Workflow 增加 Input，我們將格式資訊嵌入在 prompt 中傳遞
    effective_prompt = prompt
    if slide_format == "pptx":
        effective_prompt = f"__FORMAT:pptx__{prompt}"

    payload = {
        "ref": GH_BRANCH,
        "inputs": {
            "url": url,
            "prompt": effective_prompt,
            "chat_id": str(chat_id),
            "message_id": str(message_id)
        }
    }

    headers = {
        "Authorization": f"Bearer {GH_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)

        if response.status_code == 204:
            logger.info(f"✅ GitHub Actions (Slide) 觸發成功：{url[:60]} ({slide_format})")
            return True
        else:
            logger.error(
                f"❌ GitHub Actions (Slide) 觸發失敗：{response.status_code} - {response.text}"
            )
            return False

    except httpx.TimeoutException:
        logger.error("GitHub API 請求逾時")
        return False
    except Exception as e:
        logger.error(f"GitHub API 請求異常: {e}")
        return False
