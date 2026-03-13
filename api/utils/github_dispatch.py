import os
import httpx
import logging
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# GitHub 配置
GH_PAT = os.environ.get("GH_PAT_WORKFLOW")
GH_OWNER = os.environ.get("GH_REPO_OWNER")
GH_REPO = os.environ.get("GH_REPO_NAME")
GH_BRANCH = os.environ.get("GH_REPO_BRANCH", "main")

def get_hashed_id(chat_id: str) -> str:
    """將 chat_id 轉換為不具識別性的雜湊 ID (隱私保護)"""
    return hashlib.sha256(str(chat_id).encode()).hexdigest()[:12]

async def dispatch_group_workflow(chat_id: str) -> bool:
    """觸發指定群組的執行任務"""
    if not all([GH_PAT, GH_OWNER, GH_REPO]): return False
    api_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/workflows/execute-group.yml/dispatches"
    payload = {"ref": GH_BRANCH, "inputs": {"chat_id": str(chat_id)}}
    headers = {"Authorization": f"Bearer {GH_PAT}", "Accept": "application/vnd.github+json"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(api_url, json=payload, headers=headers)
        return resp.status_code == 204
    except Exception: return False

async def dispatch_nlm_workflow(url: str, prompt: str = "", chat_id: str = "", message_id: str = ""):
    api_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/workflows/nlm-on-demand.yml/dispatches"
    payload = {"ref": GH_BRANCH, "inputs": {"url": url, "prompt": prompt, "chat_id": str(chat_id), "message_id": str(message_id)}}
    headers = {"Authorization": f"Bearer {GH_PAT}", "Accept": "application/vnd.github+json"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(api_url, json=payload, headers=headers)
        return resp.status_code == 204
    except Exception: return False

async def dispatch_artifact_workflow(url: str, prompt: str = "", chat_id: str = "", message_id: str = "", slide_format: str = "pdf", slide_lang: str = "zh-TW", artifact_type: str = "slide_deck"):
    meta_prefix = f"__META:{slide_lang},{slide_format},{artifact_type}__"
    effective_prompt = f"{meta_prefix}{prompt}"
    api_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/workflows/slide-on-demand.yml/dispatches"
    payload = {"ref": GH_BRANCH, "inputs": {"url": url, "prompt": effective_prompt, "chat_id": str(chat_id), "message_id": str(message_id)}}
    headers = {"Authorization": f"Bearer {GH_PAT}", "Accept": "application/vnd.github+json"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(api_url, json=payload, headers=headers)
        return resp.status_code == 204
    except Exception: return False
