"""
GitHub Actions workflow_dispatch 觸發器
Vercel 透過此模組呼叫 GitHub API 啟動 nlm-on-demand.yml
"""
import os
import logging
import httpx

logger = logging.getLogger(__name__)

# 從環境變數讀取（需在 Vercel 設定）
GH_PAT = os.environ.get("GH_PAT_WORKFLOW", "")
GH_OWNER = os.environ.get("GH_REPO_OWNER", "")   # e.g. "michaelbothsieh-crypto"
GH_REPO = os.environ.get("GH_REPO_NAME", "")     # e.g. "LazyTube-Assistant"
GH_WORKFLOW_FILE = "nlm-on-demand.yml"
GH_BRANCH = os.environ.get("GH_BRANCH", "main")


async def dispatch_nlm_workflow(url: str, prompt: str, chat_id: str, message_id: str = "") -> bool:
    """
    觸發 GitHub Actions nlm-on-demand.yml
    回傳 True 表示觸發成功（202 Accepted）
    """
    if not all([GH_PAT, GH_OWNER, GH_REPO]):
        logger.error("缺少 GitHub 環境變數：GH_PAT_WORKFLOW, GH_REPO_OWNER, GH_REPO_NAME")
        return False

    api_url = (
        f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}"
        f"/actions/workflows/{GH_WORKFLOW_FILE}/dispatches"
    )

    payload = {
        "ref": GH_BRANCH,
        "inputs": {
            "url": url,
            "prompt": prompt,
            "chat_id": chat_id,
            "message_id": message_id
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

async def dispatch_slide_workflow(url: str, prompt: str, chat_id: str, message_id: str = "") -> bool:
    """
    觸發 GitHub Actions slide-on-demand.yml
    回傳 True 表示觸發成功（202 Accepted）
    """
    if not all([GH_PAT, GH_OWNER, GH_REPO]):
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)

        if response.status_code == 204:
            logger.info(f"✅ GitHub Actions (Slide) 觸發成功：{url[:60]}")
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
