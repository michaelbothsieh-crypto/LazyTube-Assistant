import os
import httpx
import logging
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# GitHub 配置
GH_PAT = os.environ.get("GH_PAT_WORKFLOW")
GH_OWNER = os.environ.get("GH_REPO_OWNER")
GH_REPO = os.environ.get("GH_REPO_NAME")
GH_BRANCH = os.environ.get("GH_REPO_BRANCH", "main")

def tw_time_to_utc_cron(tw_time: str) -> str:
    """將台灣時間 HH:mm 轉換為 UTC 格式的 cron (mm HH * * *)"""
    try:
        h, m = map(int, tw_time.split(":"))
        # 這裡不處理日期，只處理時分偏移
        utc_h = (h - 8) % 24
        return f"{m} {utc_h} * * *"
    except Exception:
        return "0 0 * * *"

async def update_group_workflow(chat_id: str, group_subs: List[Dict[str, Any]]) -> bool:
    """
    /// 為特定的 chat_id 建立或更新獨立的 Group Workflow 檔案
    /// 檔案名稱: sub-group-[chat_id].yml
    """
    if not all([GH_PAT, GH_OWNER, GH_REPO]):
        logger.error("缺少 GitHub 環境變數，無法建立 Workflow")
        return False

    if not group_subs:
        return await delete_group_workflow(chat_id)

    safe_chat_id = str(chat_id).replace("-", "n")
    file_name = f"sub-group-{safe_chat_id}.yml"
    path = f".github/workflows/{file_name}"
    
    # 彙整所有時間點
    crons = set()
    for sub in group_subs:
        pref_time = sub.get("preferred_time")
        if pref_time:
            crons.add(tw_time_to_utc_cron(pref_time))
    
    # 若完全沒時間點，預設每 12 小時 (UTC 0, 12)
    if not crons:
        crons.add("0 0,12 * * *")

    cron_yaml = "\n".join([f"    - cron: '{c}'" for c in sorted(list(crons))])

    # 建立 YAML 內容 (群組任務模式)
    yaml_content = f"""name: Sub Group - {chat_id}

on:
  schedule:
{cron_yaml}
  workflow_dispatch:

jobs:
  execute-group-task:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install notebooklm-mcp-cli==0.4.5

      - name: Restore state from Vercel Blob
        continue-on-error: true
        env:
          BLOB_TOKEN: ${{{{ secrets.BLOB_READ_WRITE_TOKEN }}}}
        run: |
          if [ -n "$BLOB_TOKEN" ]; then
            # 透過 Python 腳本來執行安全的下載，避免 curl 直接寫入錯誤訊息
            python -c "
            import os, httpx, json
            def dl(name, default):
                try:
                    headers = {{'Authorization': f'Bearer {{os.environ[\"BLOB_TOKEN\"]}}'}}
                    resp = httpx.get(f'https://blob.vercel-storage.com/v1?prefix=state/{{name}}', headers=headers)
                    blobs = resp.json().get('blobs', [])
                    if blobs:
                        url = blobs[0]['url']
                        with open(name, 'wb') as f: f.write(httpx.get(url).content)
                    else:
                        with open(name, 'w') as f: f.write(default)
                except:
                    with open(name, 'w') as f: f.write(default)
            dl('processed_videos.txt', '')
            dl('subscriptions.json', '{{}}')
            "
          fi

      - name: Run group task
        env:
          BLOB_READ_WRITE_TOKEN: ${{{{ secrets.BLOB_READ_WRITE_TOKEN }}}}
          YT_CLIENT_ID: ${{{{ secrets.YT_CLIENT_ID }}}}
          YT_CLIENT_SECRET: ${{{{ secrets.YT_CLIENT_SECRET }}}}
          YT_REFRESH_TOKEN: ${{{{ secrets.YT_REFRESH_TOKEN }}}}
          TELEGRAM_BOT_TOKEN: ${{{{ secrets.TELEGRAM_BOT_TOKEN }}}}
          NLM_COOKIE_BASE64: ${{{{ secrets.NLM_COOKIE_BASE64 }}}}
        run: |
          python on_demand_group.py "{chat_id}"

      - name: Persist state to Vercel Blob
        if: always()
        env:
          BLOB_TOKEN: ${{{{ secrets.BLOB_READ_WRITE_TOKEN }}}}
        run: |
          if [ -n "$BLOB_TOKEN" ]; then
            [ -f processed_videos.txt ] && curl -s -X PUT -H "Authorization: Bearer $BLOB_TOKEN" -H "x-add-random-suffix: 0" --data-binary @processed_videos.txt "https://blob.vercel-storage.com/state/processed_videos.txt"
            [ -f subscriptions.json ] && curl -s -X PUT -H "Authorization: Bearer $BLOB_TOKEN" -H "x-add-random-suffix: 0" --data-binary @subscriptions.json "https://blob.vercel-storage.com/state/subscriptions.json"
          fi
"""
    
    # 準備 GitHub API 請求
    api_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/contents/{path}"
    headers = {"Authorization": f"Bearer {GH_PAT}", "Accept": "application/vnd.github+json"}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            sha = None
            resp_get = await client.get(api_url, headers=headers)
            if resp_get.status_code == 200:
                sha = resp_get.json().get("sha")

            payload = {
                "message": f"chore: update subscription workflow for group {chat_id}",
                "content": base64.b64encode(yaml_content.encode("utf-8")).decode("utf-8"),
                "branch": GH_BRANCH
            }
            if sha: payload["sha"] = sha

            resp_put = await client.put(api_url, json=payload, headers=headers)
            return resp_put.status_code in [200, 201]
    except Exception as e:
        logger.error(f"GitHub API 異常: {e}")
        return False

async def dispatch_group_workflow(chat_id: str) -> bool:
    """主動觸發特定群組的 Workflow Action (原生模式)"""
    if not all([GH_PAT, GH_OWNER, GH_REPO]): return False
    safe_chat_id = str(chat_id).replace("-", "n")
    workflow_file = f"sub-group-{safe_chat_id}.yml"
    api_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/workflows/{workflow_file}/dispatches"
    payload = {"ref": GH_BRANCH, "inputs": {}}
    headers = {"Authorization": f"Bearer {GH_PAT}", "Accept": "application/vnd.github+json"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(api_url, json=payload, headers=headers)
        return resp.status_code == 204
    except Exception: return False

async def delete_group_workflow(chat_id: str) -> bool:
    """刪除整個群組的 Workflow 檔案"""
    safe_chat_id = str(chat_id).replace("-", "n")
    path = f".github/workflows/sub-group-{safe_chat_id}.yml"
    api_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/contents/{path}"
    headers = {"Authorization": f"Bearer {GH_PAT}", "Accept": "application/vnd.github+json"}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp_get = await client.get(api_url, headers=headers)
            if resp_get.status_code != 200: return True
            sha = resp_get.json().get("sha")
            payload = {"message": f"chore: delete group workflow {chat_id}", "sha": sha, "branch": GH_BRANCH}
            resp_del = await client.request("DELETE", api_url, json=payload, headers=headers)
            return resp_del.status_code == 200
    except Exception: return False

async def dispatch_nlm_workflow(url: str, prompt: str = "", chat_id: str = "", message_id: str = ""):
    """觸發隨選 NLM 查詢工作流"""
    api_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/workflows/nlm-on-demand.yml/dispatches"
    payload = {"ref": GH_BRANCH, "inputs": {"url": url, "prompt": prompt, "chat_id": str(chat_id), "message_id": str(message_id)}}
    headers = {"Authorization": f"Bearer {GH_PAT}", "Accept": "application/vnd.github+json"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(api_url, json=payload, headers=headers)
        return resp.status_code == 204
    except Exception: return False

async def dispatch_artifact_workflow(url: str, prompt: str = "", chat_id: str = "", message_id: str = "", slide_format: str = "pdf", slide_lang: str = "zh-TW", artifact_type: str = "slide_deck"):
    """觸發簡報/圖片/報告工作流"""
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
