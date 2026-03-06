"""
LazyTube-Assistant - Vercel FastAPI 入口
負責接收 Telegram Webhook 並轉發至 GitHub Actions
"""
import os
import sys
import logging
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse

# 修正匯入路徑，確保 Vercel 能找到 app 模組
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from api.handlers.tg_webhook import handle_telegram_update

# 初始化日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LazyTube-Assistant API", version="1.0.0")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


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
