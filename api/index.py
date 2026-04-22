"""
LazyTube-Assistant FastAPI entrypoints for Telegram and external webhooks.
"""
import base64
import logging
import os
import sys

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse


project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from api.handlers.tg_webhook import handle_telegram_update
from api.utils.help_text import build_help_text
from api.utils.prompt_manager import get_nlm_prompt
from app.config import Config
from app.notifier import Notifier


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LazyTube-Assistant API", version="1.0.0")

DEFAULT_EXTERNAL_PROMPT = "請幫我整理這支影片的重點，條列 5 點摘要。"

_REDIS_HEADERS = {"Authorization": f"Bearer {Config.REDIS_TOKEN}"}


async def _fetch_redis_bytes(key: str, error_label: str) -> bytes:
    url = f"{Config.REDIS_URL}/get/{key}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=_REDIS_HEADERS)
            if resp.status_code == 200:
                b64_str = resp.json().get("result")
                if b64_str:
                    return base64.b64decode(b64_str)
    except Exception as e:
        logger.error("%s error: %s", error_label, e)
    raise HTTPException(status_code=404, detail="Not found or expired")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/report-proxy")
async def report_proxy(id: str):
    content = await _fetch_redis_bytes(f"html_report_{id}", "report_proxy")
    return Response(content=content, media_type="text/html")


@app.get("/api/pdf-proxy")
async def pdf_proxy(id: str):
    content = await _fetch_redis_bytes(f"pdf_report_{id}", "pdf_proxy")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Research_Report_{id}.pdf"},
    )


@app.post("/api/tg-webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=None),
):
    """Handle Telegram webhook updates."""
    expected_secret = Config.TG_WEBHOOK_SECRET
    if expected_secret and x_telegram_bot_api_secret_token != expected_secret:
        logger.warning("Invalid Telegram webhook secret token")
        raise HTTPException(status_code=403, detail="Invalid secret token")

    try:
        update = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    try:
        await handle_telegram_update(update)
    except Exception as exc:
        logger.error("Failed to handle Telegram update: %s", exc)

    return JSONResponse(content={"ok": True})


@app.post("/api/external-dispatch")
async def external_dispatch(
    request: Request,
    authorization: str = Header(default=None),
):
    """
    Handle external webhook dispatches, including the LINE bot relay.
    """
    expected_secret = Config.TG_WEBHOOK_SECRET
    if expected_secret and authorization != expected_secret:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        data = await request.json()
        url = data.get("url")
        prompt_raw = data.get("prompt", "")
        prompt = get_nlm_prompt(prompt_raw)
        chat_id = data.get("chat_id")
        command = str(data.get("command", "nlm")).strip().lower()

        if not chat_id:
            return JSONResponse(
                content={"ok": False, "error": "Missing params"},
                status_code=400,
            )

        allowed_list = Config.get_allowed_users()
        if allowed_list and chat_id not in allowed_list:
                logger.warning("External dispatch permission denied: %s", chat_id)
                return JSONResponse(
                    content={"ok": False, "error": "Permission denied"},
                    status_code=403,
                )

        if command in ["help", "/help"]:
            if not Notifier.send_text(chat_id, build_help_text(html=False)):
                return JSONResponse(
                    content={"ok": False, "error": "Help delivery failed"},
                    status_code=500,
                )
            return JSONResponse(content={"ok": True})

        if command == "research":
            from api.utils.github_dispatch import dispatch_research_workflow
            topic = url or prompt_raw
            mode = "deep" if "deep" in prompt_raw.lower() else "fast"
            await dispatch_research_workflow(
                topic=topic,
                mode=mode,
                chat_id=chat_id,
                message_id=data.get("message_id", "")
            )
            return JSONResponse(content={"ok": True})

        if not url:
            return JSONResponse(
                content={"ok": False, "error": "Missing params"},
                status_code=400,
            )

        if command in ["slide", "pic", "note"]:
            from api.utils.github_dispatch import dispatch_artifact_workflow

            art_map = {
                "slide": "slide_deck",
                "pic": "infographic",
                "note": "report",
            }
            await dispatch_artifact_workflow(
                url=url,
                prompt=prompt,
                chat_id=chat_id,
                artifact_type=art_map.get(command, "slide_deck"),
            )
        else:
            from api.utils.github_dispatch import dispatch_nlm_workflow

            # 外部 Hook 同樣觸發隨選 NLM 流程
            await dispatch_nlm_workflow(
                url=url,
                prompt=prompt,
                chat_id=chat_id,
                message_id=data.get("message_id", "")
            )

        return JSONResponse(content={"ok": True})
    except Exception as exc:
        logger.error("external_dispatch error: %s", exc)
        return JSONResponse(
            content={"ok": False, "error": str(exc)},
            status_code=500,
        )
