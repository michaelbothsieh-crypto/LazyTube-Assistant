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

from api.handlers.tg_webhook import TgUpdate, handle_telegram_update
from api.utils.github_dispatch import GitHubActionManager
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
        update: TgUpdate = await request.json()
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

        if command in ["threads", "/threads"]:
            if not url:
                return JSONResponse(
                    content={"ok": False, "error": "Missing Threads URL"},
                    status_code=400,
                )
            import asyncio

            from app.threads_analyzer import analyze_threads_url

            analysis = await asyncio.to_thread(analyze_threads_url, url)
            if analysis.video_url:
                await asyncio.to_thread(Notifier.send_video_url, chat_id, analysis.video_url)
            elif analysis.image_url:
                await asyncio.to_thread(Notifier.send_photo_url, chat_id, analysis.image_url)
            Notifier.send_text(chat_id, analysis.format())
            return JSONResponse(content={"ok": True})

        # ── Podcast 指令（TG / LINE 通用）──────────────────────────────────
        if command in ["podcast", "/podcast"]:
            rss_url = url or ""
            episode_number = str(data.get("episode_number", "")).strip()

            if not rss_url:
                from app.podcast_state import get_subscriptions
                subs = get_subscriptions()
                rss_url = next(iter(subs), "https://feeds.soundon.fm/podcasts/954689a5-3096-43a4-a80b-7810b219cef3.xml")

            # Apple 單集 URL（含 ?i=）必須原樣傳給 Actions，讓 scanner 萃取集數線索
            is_apple_episode_url = "podcasts.apple.com" in rss_url and "?i=" in rss_url

            if not is_apple_episode_url and not rss_url.endswith(".xml") and "feeds." not in rss_url:
                from app.podcast_rss_resolver import resolve_rss_fast
                resolved = resolve_rss_fast(rss_url)
                if resolved:
                    rss_url = resolved

            Notifier.send_text(chat_id, "🎙️ Podcast 分析已建立，預計 5-15 分鐘後完成並推送。")

            success = await GitHubActionManager.dispatch(
                "podcast-on-demand.yml",
                {
                    "rss_url": rss_url,
                    "mode": "latest",
                    "episode_number": episode_number,
                    "chat_id": str(chat_id),
                    "message_id": data.get("message_id", ""),
                },
                timeout=10.0,
            )
            if not success:
                logger.error("podcast-on-demand dispatch failed for chat_id=%s", chat_id)
                Notifier.send_text(chat_id, "❌ Podcast 任務派送失敗，請稍後再試。")
            return JSONResponse(content={"ok": True})

        if command in ["subpodcast", "/subpodcast"]:
            from app.podcast_rss_resolver import resolve_rss
            from app.podcast_state import add_subscription
            from app.state_manager import StateManager
            if not url:
                Notifier.send_text(chat_id, "用法：subpodcast <podcast_url>")
                return JSONResponse(content={"ok": False, "error": "missing url"}, status_code=400)

            # 解析 RSS
            rss_url, label = resolve_rss(url)
            if not rss_url:
                Notifier.send_text(chat_id, f"❌ 無法解析 RSS：{url}")
                return JSONResponse(content={"ok": False, "error": "rss resolve failed"}, status_code=422)

            added = add_subscription(rss_url, label)
            await StateManager.sync_to_blob("processed_podcasts.json")
            if added:
                Notifier.send_text(chat_id, f"✅ 已訂閱：{label}\n{rss_url}")
            else:
                Notifier.send_text(chat_id, f"⚠️ 已訂閱過：{label}\n{rss_url}")
            return JSONResponse(content={"ok": True})
        # ──────────────────────────────────────────────────────────────────

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
