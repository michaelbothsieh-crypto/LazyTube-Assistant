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
    """
    Telegram Webhook 端點
    1. 驗證 Secret Token
    2. 解析指令
    3. 觸發 GitHub Actions（非同步）
    4. 立即回應 200 OK
    """
    # --- 安全驗證 ---
    expected_secret = os.environ.get("TG_WEBHOOK_SECRET", "")
    if expected_secret and x_telegram_bot_api_secret_token != expected_secret:
        logger.warning(f"收到無效的 Webhook Secret Token，已拒絕請求")
        raise HTTPException(status_code=403, detail="Invalid secret token")

    # --- 解析 Telegram Update ---
    try:
        update = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # --- 處理指令（非同步觸發 Actions，立即返回） ---
    try:
        await handle_telegram_update(update)
    except Exception as e:
        logger.error(f"處理 Telegram Update 時發生錯誤: {e}")
        # 即使出錯也要回 200，避免 Telegram 無限重試

    return JSONResponse(content={"ok": True})
