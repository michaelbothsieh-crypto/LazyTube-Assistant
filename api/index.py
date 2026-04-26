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

_HOMEPAGE_HTML = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LazyTube Assistant — AI 財經 Podcast 分析平台</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #0a0e1a;
      --surface: #111827;
      --surface2: #1a2236;
      --border: rgba(255,255,255,0.08);
      --primary: #3b82f6;
      --primary-glow: rgba(59,130,246,0.3);
      --accent: #06b6d4;
      --green: #10b981;
      --yellow: #f59e0b;
      --red: #ef4444;
      --text: #f1f5f9;
      --muted: #64748b;
    }
    html { scroll-behavior: smooth; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: "Inter", "Noto Sans TC", sans-serif;
      line-height: 1.6;
      min-height: 100vh;
    }

    /* ── Top Bar ── */
    .topbar {
      position: fixed; top: 0; left: 0; right: 0; z-index: 100;
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 32px; height: 56px;
      background: rgba(10,14,26,0.85);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border);
    }
    .logo { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1rem; }
    .logo-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--primary); box-shadow: 0 0 10px var(--primary-glow); animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
    .status-pill {
      display: flex; align-items: center; gap: 6px;
      background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.25);
      padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; color: var(--green);
    }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); animation: pulse 1.5s infinite; }

    /* ── Hero ── */
    .hero {
      padding: 120px 32px 80px;
      text-align: center;
      background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(59,130,246,0.12) 0%, transparent 70%);
    }
    .hero-badge {
      display: inline-flex; align-items: center; gap: 8px;
      background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.3);
      padding: 6px 16px; border-radius: 20px; font-size: 0.8rem;
      color: var(--primary); margin-bottom: 24px;
    }
    .hero h1 {
      font-size: clamp(2.2rem, 5vw, 3.5rem);
      font-weight: 700; line-height: 1.15; margin-bottom: 16px;
      background: linear-gradient(135deg, #fff 30%, var(--primary) 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .hero p { font-size: 1.15rem; color: var(--muted); max-width: 560px; margin: 0 auto 40px; }
    .hero-actions { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
    .btn {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 12px 24px; border-radius: 8px; font-size: 0.9rem; font-weight: 500;
      text-decoration: none; transition: all .2s;
    }
    .btn-primary { background: var(--primary); color: #fff; }
    .btn-primary:hover { background: #2563eb; box-shadow: 0 0 24px var(--primary-glow); transform: translateY(-1px); }
    .btn-ghost { background: var(--surface2); color: var(--text); border: 1px solid var(--border); }
    .btn-ghost:hover { background: rgba(255,255,255,0.06); transform: translateY(-1px); }

    /* ── Stats Bar ── */
    .stats { display: flex; justify-content: center; gap: 0; flex-wrap: wrap; padding: 0 32px 64px; }
    .stat { padding: 20px 40px; text-align: center; border-right: 1px solid var(--border); }
    .stat:last-child { border-right: none; }
    .stat-num { font-size: 2rem; font-weight: 700; color: var(--primary); }
    .stat-label { font-size: 0.8rem; color: var(--muted); margin-top: 2px; }

    /* ── Grid ── */
    .section { padding: 0 32px 80px; max-width: 1100px; margin: 0 auto; }
    .section-title { font-size: 1.4rem; font-weight: 600; margin-bottom: 24px; display: flex; align-items: center; gap: 10px; }
    .section-title::after { content: ''; flex: 1; height: 1px; background: var(--border); }
    .bento { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
    .card {
      background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
      padding: 24px; transition: border-color .2s, transform .2s;
    }
    .card:hover { border-color: rgba(59,130,246,0.4); transform: translateY(-2px); }
    .card-icon { font-size: 1.6rem; margin-bottom: 12px; }
    .card h3 { font-size: 1rem; font-weight: 600; margin-bottom: 6px; }
    .card p { font-size: 0.85rem; color: var(--muted); }
    .card-tag {
      display: inline-block; margin-top: 12px;
      padding: 3px 10px; border-radius: 12px; font-size: 0.72rem; font-weight: 500;
    }
    .tag-green { background: rgba(16,185,129,0.1); color: var(--green); }
    .tag-blue { background: rgba(59,130,246,0.1); color: var(--primary); }
    .tag-yellow { background: rgba(245,158,11,0.1); color: var(--yellow); }

    /* ── API Endpoints ── */
    .endpoint {
      background: var(--surface2); border: 1px solid var(--border); border-radius: 8px;
      padding: 16px 20px; margin-bottom: 10px; display: flex; align-items: flex-start; gap: 16px;
    }
    .method {
      padding: 3px 10px; border-radius: 6px; font-size: 0.72rem; font-weight: 700;
      font-family: monospace; flex-shrink: 0; margin-top: 2px;
    }
    .get { background: rgba(16,185,129,0.15); color: var(--green); }
    .post { background: rgba(59,130,246,0.15); color: var(--primary); }
    .ep-path { font-family: monospace; font-size: 0.9rem; color: var(--accent); }
    .ep-desc { font-size: 0.8rem; color: var(--muted); margin-top: 3px; }

    /* ── Flow ── */
    .flow { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 24px; background: var(--surface2); border-radius: 12px; border: 1px solid var(--border); }
    .flow-step { padding: 8px 16px; background: var(--surface); border-radius: 8px; font-size: 0.85rem; border: 1px solid var(--border); }
    .flow-arrow { color: var(--primary); font-size: 1.1rem; }

    /* ── Footer ── */
    footer { padding: 32px; text-align: center; color: var(--muted); font-size: 0.8rem; border-top: 1px solid var(--border); }
    footer a { color: var(--primary); text-decoration: none; }
  </style>
</head>
<body>
  <nav class="topbar">
    <div class="logo"><div class="logo-dot"></div> LazyTube Assistant</div>
    <div class="status-pill"><div class="status-dot"></div> API 運行中</div>
  </nav>

  <section class="hero">
    <div class="hero-badge">🤖 AI 財經 Podcast 分析平台</div>
    <h1>讓 AI 幫你追蹤<br>所有財經 KOL 觀點</h1>
    <p>自動下載 Podcast、AI 轉錄分析、推送 Telegram，每集都不漏</p>
    <div class="hero-actions">
      <a href="/api/health" class="btn btn-primary">🔍 API 健康檢查</a>
      <a href="https://github.com/michaelbothsieh-crypto/LazyTube-Assistant" target="_blank" class="btn btn-ghost">📦 GitHub</a>
    </div>
  </section>

  <div class="stats">
    <div class="stat"><div class="stat-num">5+</div><div class="stat-label">AI 分析指令</div></div>
    <div class="stat"><div class="stat-num">∞</div><div class="stat-label">訂閱 Podcast 數量</div></div>
    <div class="stat"><div class="stat-num">~5分</div><div class="stat-label">每集分析時間</div></div>
    <div class="stat"><div class="stat-num">24h</div><div class="stat-label">自動定時掃描</div></div>
  </div>

  <div class="section">
    <h2 class="section-title">🎯 核心功能</h2>
    <div class="bento">
      <div class="card">
        <div class="card-icon">🎙️</div>
        <h3>Podcast 財經分析</h3>
        <p>輸入 RSS 連結或節目名稱，自動下載音檔並用 AI 深度分析財經觀點、焦點標的，生成 Bloomberg 風格報告</p>
        <span class="card-tag tag-green">指令：/podcast</span>
      </div>
      <div class="card">
        <div class="card-icon">📺</div>
        <h3>YouTube 影片摘要</h3>
        <p>傳入 YouTube 連結，AI 自動轉錄並整理重點摘要，支援財經、科技等多種 Prompt 模板</p>
        <span class="card-tag tag-blue">指令：/nlm</span>
      </div>
      <div class="card">
        <div class="card-icon">🔬</div>
        <h3>Deep Research 報告</h3>
        <p>輸入任意主題，AI 自動搜集資料並生成多維度研究報告，以 PDF 形式推送</p>
        <span class="card-tag tag-yellow">指令：/research</span>
      </div>
      <div class="card">
        <div class="card-icon">🔔</div>
        <h3>RSS 定時訂閱</h3>
        <p>訂閱任意 Podcast RSS，每天自動掃描新集數，有新集立即分析並推送 Telegram</p>
        <span class="card-tag tag-green">指令：/subpodcast</span>
      </div>
      <div class="card">
        <div class="card-icon">📊</div>
        <h3>HTML 互動報告</h3>
        <p>分析結果以精美 HTML 報告呈現，儲存於 Redis，透過短連結在 Telegram 直接點閱</p>
        <span class="card-tag tag-blue">端點：/api/report-proxy</span>
      </div>
      <div class="card">
        <div class="card-icon">⚡</div>
        <h3>音檔智能壓縮</h3>
        <p>使用 ffmpeg 自動將音檔壓縮至 32kbps mono，上傳速度提升 4 倍，大幅縮短分析等待時間</p>
        <span class="card-tag tag-yellow">自動執行</span>
      </div>
    </div>
  </div>

  <div class="section">
    <h2 class="section-title">🔄 自動化流程</h2>
    <div class="flow">
      <div class="flow-step">📱 Telegram /podcast</div>
      <div class="flow-arrow">→</div>
      <div class="flow-step">⚡ GitHub Actions</div>
      <div class="flow-arrow">→</div>
      <div class="flow-step">⬇️ 下載 + 壓縮音檔</div>
      <div class="flow-arrow">→</div>
      <div class="flow-step">🤖 AI 轉錄分析</div>
      <div class="flow-arrow">→</div>
      <div class="flow-step">📄 生成 HTML 報告</div>
      <div class="flow-arrow">→</div>
      <div class="flow-step">💬 推送 Telegram</div>
    </div>
  </div>

  <div class="section">
    <h2 class="section-title">🔌 API 端點</h2>
    <div class="endpoint">
      <span class="method get">GET</span>
      <div><div class="ep-path">/api/health</div><div class="ep-desc">健康檢查，確認服務正常運行</div></div>
    </div>
    <div class="endpoint">
      <span class="method get">GET</span>
      <div><div class="ep-path">/api/report-proxy?id={id}</div><div class="ep-desc">透過 Redis 取得 HTML 分析報告（24h 有效）</div></div>
    </div>
    <div class="endpoint">
      <span class="method get">GET</span>
      <div><div class="ep-path">/api/pdf-proxy?id={id}</div><div class="ep-desc">下載 PDF 格式研究報告</div></div>
    </div>
    <div class="endpoint">
      <span class="method post">POST</span>
      <div><div class="ep-path">/api/tg-webhook</div><div class="ep-desc">Telegram Bot Webhook 接收端點</div></div>
    </div>
    <div class="endpoint">
      <span class="method post">POST</span>
      <div><div class="ep-path">/api/external-dispatch</div><div class="ep-desc">外部系統整合端點（LINE Bot、第三方 Webhook）</div></div>
    </div>
  </div>

  <footer>
    Built with FastAPI · Deployed on Vercel · Powered by NotebookLM &amp; GitHub Actions<br>
    <a href="/api/health">Health Check</a> · <a href="https://github.com/michaelbothsieh-crypto/LazyTube-Assistant" target="_blank">GitHub</a>
  </footer>
</body>
</html>"""


@app.get("/", response_class=Response)
async def homepage():
    return Response(content=_HOMEPAGE_HTML, media_type="text/html")



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

        # ── Podcast 指令（TG / LINE 通用）──────────────────────────────────
        if command in ["podcast", "/podcast"]:
            # 單次查詢最新一集
            rss_url = url or ""
            if not rss_url:
                # 從訂閱清單取第一個
                from app.podcast_state import get_subscriptions
                subs = get_subscriptions()
                rss_url = next(iter(subs), "https://feeds.soundon.fm/podcasts/954689a5-3096-43a4-a80b-7810b219cef3.xml")

            # 若傳入的是頁面 URL，嘗試解析 RSS
            if rss_url and not (rss_url.endswith(".xml") or "feeds." in rss_url):
                from app.podcast_rss_resolver import resolve_rss
                resolved, _ = resolve_rss(rss_url)
                if resolved:
                    rss_url = resolved

            success = await GitHubActionManager.dispatch(
                "podcast-on-demand.yml",
                {"rss_url": rss_url, "mode": "latest", "chat_id": str(chat_id), "message_id": data.get("message_id", "")},
                timeout=10.0,
            )
            if not success:
                logger.error("podcast-on-demand dispatch failed for chat_id=%s", chat_id)
                if not Notifier.send_text(chat_id, "❌ Podcast 任務派送失敗，請稍後再試。"):
                    return JSONResponse(content={"ok": False, "error": "dispatch failed"}, status_code=500)
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

