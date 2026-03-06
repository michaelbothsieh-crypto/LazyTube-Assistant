"""
LazyTube-Assistant - Vercel FastAPI 入口
負責接收 Telegram Webhook 並轉發至 GitHub Actions
"""
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import os
import httpx
import logging

# 子模組（handlers）
from api.handlers.tg_webhook import handle_telegram_update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LazyTube-Assistant API", version="1.0.0")


@app.get("/api/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "ok", "service": "LazyTube-Assistant"}


@app.post("/api/tg-webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=None)
):
...
    return JSONResponse(content={"ok": True})


@app.post("/api/external-dispatch")
async def external_dispatch(
    request: Request,
    authorization: str = Header(default=None)
):
    """
    接收來自外部（如 LINE 機器人）的摘要請求
    payload: { "url": "...", "prompt": "...", "chat_id": "..." }
    """
    # 驗證 Secret (借用 TG_WEBHOOK_SECRET 作為 API Key)
    expected_secret = os.environ.get("TG_WEBHOOK_SECRET", "")
    if expected_secret and authorization != expected_secret:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        data = await request.json()
        url = data.get("url")
        prompt = data.get("prompt", "請用繁體中文列出 5 個核心重點。")
        chat_id = data.get("chat_id")

        if not url or not chat_id:
            return JSONResponse(content={"ok": False, "error": "Missing params"}, status_code=400)

        # 觸發 GitHub Actions
        from api.utils.github_dispatch import dispatch_nlm_workflow
        await dispatch_nlm_workflow(url=url, prompt=prompt, chat_id=chat_id)
        
        return JSONResponse(content={"ok": True})
    except Exception as e:
        logger.error(f"external_dispatch 錯誤: {e}")
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)
