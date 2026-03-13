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

def tw_time_to_utc_cron(tw_time: str) -> str:
    """將台灣時間 HH:mm 轉換為 UTC 格式的 cron"""
    try:
        h, m = map(int, tw_time.split(":"))
        utc_h = (h - 8) % 24
        return f"{m} {utc_h} * * *"
    except Exception: return "0 0 * * *"

async def update_group_workflow(chat_id: str, group_subs: List[Dict[str, Any]]) -> bool:
    """為特定的 chat_id 建立或更新獨立的 Group Workflow 檔案 (使用雜湊 ID 保護隱私)"""
    if not all([GH_PAT, GH_OWNER, GH_REPO]): return False
    if not group_subs: return await delete_group_workflow(chat_id)

    hashed_id = get_hashed_id(chat_id)
    file_name = f"sub-group-{hashed_id}.yml"
    path = f".github/workflows/{file_name}"
    
    crons = set()
    for sub in group_subs:
        pref_time = sub.get("preferred_time")
        if pref_time: crons.add(tw_time_to_utc_cron(pref_time))
    if not crons: crons.add("0 0,12 * * *")
    cron_yaml = "\n".join([f"    - cron: '{c}'" for c in sorted(list(crons))])

    # 注意：在 YAML 與腳本參數中均使用 hashed_id 以保護隱私
    yaml_content = f"""name: Task - {hashed_id}

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
            cat << 'INNER_EOF' > sync_state.py
import os, json, time, urllib.request as r, hashlib
def get_h(cid): return hashlib.sha256(str(cid).encode()).hexdigest()[:12]
def dl(name, default, retry=3):
    headers = {{'Authorization': f'Bearer {{os.environ.get("BLOB_TOKEN")}}', 'x-api-version': '1'}}
    for i in range(retry):
        try:
            list_url = f'https://blob.vercel-storage.com/v1?prefix=state/{{name}}'
            req = r.Request(list_url, headers=headers)
            with r.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                if data.get('blobs'):
                    url = data['blobs'][0]['url']
                    content = r.urlopen(url).read()
                    if name == 'subscriptions.json':
                        s = json.loads(content.decode())
                        # 檢查 JSON 中是否有任何群組 ID 雜湊後與當前 hashed_id 匹配
                        if not any(get_h(k) == '{hashed_id}' for k in s.keys()):
                            print(f'Sync delay for {hashed_id}, retrying {{i+1}}...'); time.sleep(5); continue
                    with open(name, 'wb') as f: f.write(content)
                    print(f'Successfully downloaded {{name}}'); return
        except Exception as e: print(f'Retry failed: {{e}}')
        time.sleep(5)
    with open(name, 'w') as f: f.write(default)
dl('processed_videos.txt', '')
dl('subscriptions.json', '{{}}')
INNER_EOF
            python sync_state.py
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
          # 傳入雜湊後的 ID
          python on_demand_group.py "{hashed_id}"

      - name: Persist state to Vercel Blob
        if: always()
        env:
          BLOB_TOKEN: ${{{{ secrets.BLOB_READ_WRITE_TOKEN }}}}
        run: |
          if [ -n "$BLOB_TOKEN" ]; then
            [ -f processed_videos.txt ] && curl -s -X PUT -H "Authorization: Bearer $BLOB_TOKEN" -H "x-api-version: 1" -H "x-add-random-suffix: 0" --data-binary @processed_videos.txt "https://blob.vercel-storage.com/v1/upload/state/processed_videos.txt" > /dev/null
            [ -f subscriptions.json ] && curl -s -X PUT -H "Authorization: Bearer $BLOB_TOKEN" -H "x-api-version: 1" -H "x-add-random-suffix: 0" --data-binary @subscriptions.json "https://blob.vercel-storage.com/v1/upload/state/subscriptions.json" > /dev/null
            echo "✅ State persistence completed."
          fi
"""
    
    api_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/contents/{path}"
    headers = {"Authorization": f"Bearer {GH_PAT}", "Accept": "application/vnd.github+json"}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            sha = None
            resp_get = await client.get(api_url, headers=headers)
            if resp_get.status_code == 200: sha = resp_get.json().get("sha")
            payload = {
                "message": f"chore: update subscription workflow for task {hashed_id}",
                "content": base64.b64encode(yaml_content.encode("utf-8")).decode("utf-8"),
                "branch": GH_BRANCH
            }
            if sha: payload["sha"] = sha
            resp_put = await client.put(api_url, json=payload, headers=headers)
            return resp_put.status_code in [200, 201]
    except Exception: return False

async def dispatch_group_workflow(chat_id: str) -> bool:
    """主動觸發特定群組的 Workflow Action (使用雜湊 ID)"""
    if not all([GH_PAT, GH_OWNER, GH_REPO]): return False
    hashed_id = get_hashed_id(chat_id)
    workflow_file = f"sub-group-{hashed_id}.yml"
    api_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/workflows/{workflow_file}/dispatches"
    payload = {"ref": GH_BRANCH, "inputs": {}}
    headers = {"Authorization": f"Bearer {GH_PAT}", "Accept": "application/vnd.github+json"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(api_url, json=payload, headers=headers)
        return resp.status_code == 204
    except Exception: return False

async def delete_group_workflow(chat_id: str) -> bool:
    """刪除整個群組的 Workflow 檔案 (使用雜湊 ID)"""
    hashed_id = get_hashed_id(chat_id)
    path = f".github/workflows/sub-group-{hashed_id}.yml"
    api_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/contents/{path}"
    headers = {"Authorization": f"Bearer {GH_PAT}", "Accept": "application/vnd.github+json"}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp_get = await client.get(api_url, headers=headers)
            if resp_get.status_code != 200: return True
            sha = resp_get.json().get("sha")
            payload = {"message": f"chore: delete task workflow {hashed_id}", "sha": sha, "branch": GH_BRANCH}
            resp_del = await client.request("DELETE", api_url, json=payload, headers=headers)
            return resp_del.status_code == 200
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
