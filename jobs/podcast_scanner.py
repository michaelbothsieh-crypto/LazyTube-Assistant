"""
podcast_scanner.py — 每日定時掃描 Podcast RSS，上傳 NLM 取得財經分析，推送 Telegram。

環境變數：
  PODCAST_RSS_URLS   : 逗號分隔 RSS（優先於訂閱清單）
  CUSTOM_PROMPT      : prompt 關鍵字（預設 "finance"）
  PODCAST_MODE       : "daily"（新集數）| "latest"（只取最新一集，on-demand 用）
  PODCAST_CHAT_ID    : on-demand 指定回傳的 chat_id
  PODCAST_MESSAGE_ID : on-demand 的 pending message id
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import feedparser
import requests

# ── 確保 project root 在 path ──────────────────────────────────────────────
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.auth import AuthManager
from app.config import Config
from app.db_writer import compute_and_write_consensus, ensure_kol, write_episode
from app.notebook.notebook_session import NotebookSession
from app.notebook.parsing import parse_query_output
from app.notebook.runner import NotebookRunner
from app.notifier.reporting import generate_podcast_html_report
from app.notifier.service import Notifier
from app.podcast_cache import get_cached_analysis, set_cached_analysis
from app.podcast_state import get_subscriptions, init_empty, is_processed, mark_processed
from api.utils.prompt_manager import get_nlm_prompt

MAX_EPISODES_PER_RUN = 2
DOWNLOAD_TIMEOUT_SEC = 300
MP3_SIZE_LIMIT_MB = 200


def _looks_like_rss_url(url: str) -> bool:
    """判斷 URL 是否已是 RSS feed（不需再解析）。"""
    markers = [".xml", "/rss", "/feed", "feeds.", "rss2", "podcast.xml"]
    return any(m in url.lower() for m in markers)


def _build_episode_prompt(base_prompt: str, ep: dict) -> str:
    """
    將 RSS 元資料注入 prompt 開頭，讓 NLM 以正確人名、節目名稱作為
    音訊轉錄的修正參考。通用於所有頻道，不需手動設定字典。

    注入格式（只有有值才加入）：
      【本集背景資訊】
      節目名稱：游庭皓的財經皓角
      主持人：游庭皓
      本集標題：2026/4/24 費半破萬點...
    """
    lines = []
    if ep.get("feed_title"):
        lines.append(f"節目名稱：{ep['feed_title']}")
    if ep.get("feed_author"):
        lines.append(f"主持人：{ep['feed_author']}")
    if ep.get("title"):
        lines.append(f"本集標題：{ep['title']}")

    if not lines:
        return base_prompt

    context = "【本集背景資訊（請以此修正音訊中的人名與節目專有名詞）】\n" + "\n".join(lines)
    return f"{context}\n\n{base_prompt}"


def _parse_nlm_analysis(analysis: str) -> tuple[str, list[str], str]:
    """
    從 NLM podcast prompt 的分析結果中提取結構化資料：
    - summary  : 本集結論（2-3 句，用於 DB 摘要欄）
    - stocks   : 提及的股票代碼列表（台股 4 碼 + 美股大寫）
    - sentiment: 'bullish' | 'bearish' | 'neutral'

    對應 podcast prompt 格式：
      【文字紀錄】 ...
      【投資倒數小結】
      1. 台美股焦點標的：...
      2. 本集結論：...
    """
    # ── 摘要：優先取「2. 本集結論」段落 ─────────────────────────────────
    summary = ""
    m = re.search(r'2[\.、]\s*本集結論[：:]\s*(.*?)(?=\n\n|\Z)', analysis, re.DOTALL)
    if m:
        summary = m.group(1).strip()
    if not summary:
        # Fallback：取【投資倒數小結】後第一段
        m2 = re.search(r'【投資倒數小結】\s*(.*?)(?=\n\n\n|\Z)', analysis, re.DOTALL)
        if m2:
            summary = m2.group(1).strip()[:400]
    if not summary:
        summary = analysis[:400].strip()

    # ── 股票代碼：從「1. 台美股焦點標的」段落提取 ────────────────────────
    stocks: list[str] = []
    m3 = re.search(r'1[\.、]\s*台美股焦點標的[：:](.*?)(?=2[\.、]|\Z)', analysis, re.DOTALL)
    if m3:
        section = m3.group(1)
        tw = re.findall(r'\b(\d{4})\b', section)
        us = re.findall(r'\b([A-Z]{2,5})\b', section)
        skip = {
            'AI', 'IT', 'US', 'TW', 'Q1', 'Q2', 'Q3', 'Q4',
            'EPS', 'ETF', 'PE', 'PB', 'EV', 'IPO', 'RSI', 'MA',
            'CEO', 'CFO', 'GDP', 'CPI', 'PCE', 'FED', 'ECB',
        }
        stocks = list(dict.fromkeys(tw + [t for t in us if t not in skip]))

    # 同時比對中文公司名 → ticker（補充純中文文本的情況）
    cn_map: dict[str, str] = {
        "台積電": "2330", "輝達": "NVDA", "英偉達": "NVDA",
        "特斯拉": "TSLA", "超微": "AMD", "蘋果": "AAPL",
        "微軟": "MSFT", "谷歌": "GOOGL", "亞馬遜": "AMZN",
        "鴻海": "2317", "聯發科": "2454", "廣達": "2382",
        "富邦金": "2881", "國泰金": "2882", "大立光": "3008",
        "台達電": "2308", "英特爾": "INTC", "美光": "MU",
        "高通": "QCOM", "博通": "AVGO", "Meta": "META",
        "ARM": "ARM", "台塑": "1301", "中鋼": "2002",
        "聯電": "2303", "日月光": "3711", "瑞昱": "2379",
        "緯創": "3231", "技嘉": "2376", "微星": "2377",
    }
    for cn, ticker in cn_map.items():
        if cn in analysis and ticker not in stocks:
            stocks.append(ticker)

    # ── 情緒判斷：正負關鍵詞計分 ─────────────────────────────────────────
    bullish_kw = ['看多', '偏多', '樂觀', '買進', '做多', '突破', '強勢',
                  '利多', '長多', '看好', '正向', '走強', '上攻', '偏樂']
    bearish_kw = ['看空', '偏空', '謹慎', '賣出', '做空', '回檔', '壓力',
                  '利空', '下跌', '危險', '風險高', '弱勢', '偏保守', '下行']
    bull = sum(analysis.count(w) for w in bullish_kw)
    bear = sum(analysis.count(w) for w in bearish_kw)
    if bull > bear + 2:
        sentiment = 'bullish'
    elif bear > bull + 2:
        sentiment = 'bearish'
    else:
        sentiment = 'neutral'

    return summary, stocks, sentiment


def _apple_episode_hint(url: str) -> dict:
    """
    偵測 Apple Podcasts 單集 URL（含 ?i= 參數）並萃取比對線索。
    URL 格式：podcasts.apple.com/.../podcast/{slug}/id{show_id}?i={episode_trackid}
    回傳 {'date': 'YYYY-MM-DD', 'slug': '...'}，若非單集 URL 則回傳 {}。
    """
    from urllib.parse import urlparse, parse_qs, unquote
    parsed = urlparse(url)
    if "podcasts.apple.com" not in parsed.netloc:
        return {}
    if "i" not in parse_qs(parsed.query):
        return {}

    # 從 path 找到 episode slug（跳過 locale、"podcast"、"id{digits}" 段）
    path = unquote(parsed.path)
    slug = ""
    for seg in path.split("/"):
        if not seg:
            continue
        if re.match(r"id\d+$", seg):
            continue
        if seg == "podcast":
            continue
        if re.match(r"[a-z]{2}$", seg):   # locale e.g. "tw"
            continue
        slug = seg
        break

    hint: dict = {"slug": slug, "date": ""}
    # slug 通常以 YYYY-M-D 開頭，例如 "2026-4-24-五-費半破萬點..."
    date_m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", slug)
    if date_m:
        y, mo, d = date_m.groups()
        hint["date"] = f"{y}-{int(mo):02d}-{int(d):02d}"
    return hint


def format_rss_date(raw: str) -> str:
    """
    將 RSS 各種日期格式統一轉為 YYYY-MM-DD。
    支援：
      RFC 2822  "Fri, 24 Apr 2026 02:00:00 +0000"
      ISO 8601  "2026-04-24T02:00:00+00:00"
      已是 YYYY-MM-DD 格式則直接回傳前 10 字元
    """
    if not raw:
        return ""
    from email.utils import parsedate
    import calendar
    # 嘗試 RFC 2822
    try:
        t = parsedate(raw)
        if t:
            return f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d}"
    except Exception:
        pass
    # 嘗試 ISO 8601 / 其他帶 T 的格式
    try:
        import datetime
        dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    # fallback：截取前 10 字元（若已是 YYYY-MM-DD）
    return raw[:10]


# ── RSS 掃描 ──────────────────────────────────────────────────────────────

def fetch_new_episodes(
    rss_url: str,
    mode: str = "daily",
    chat_id: str = "",
    episode_number: str = "",
) -> list[dict]:
    """
    掃描單一 RSS，回傳待處理的集數。
    mode="latest" + episode_number 空  → 取最新一集（不做 dedup）
    mode="latest" + episode_number="655" → 在 title 中搜尋含 "655" 的集數
    mode="latest" + Apple episode URL   → 從 URL 萃取日期/關鍵字比對正確集數
    mode="daily"  → 以 (rss_url, chat_id) 為複合 key 過濾已處理 GUID
    """
    # 在解析 RSS 前先記錄 Apple 單集 URL 的線索（解析後 rss_url 會被替換掉）
    apple_hint = _apple_episode_hint(rss_url)
    if apple_hint:
        print(f"  [INFO] 偵測到 Apple 單集 URL，比對線索：date={apple_hint['date']} slug={apple_hint['slug'][:40]}")

    # 保險層：若收到 Apple Podcasts / SoundOn / Firstory 頁面 URL，先解析成 RSS
    if not _looks_like_rss_url(rss_url):
        from app.podcast_rss_resolver import resolve_rss_fast
        resolved = resolve_rss_fast(rss_url)
        if resolved:
            print(f"  [OK] URL 已解析：{rss_url[:60]} → {resolved[:60]}")
            rss_url = resolved
        else:
            print(f"  [FAIL] 無法解析 URL 為 RSS：{rss_url}")
            return []

    print(f"📡 揉描 RSS：{rss_url}")

    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        print(f"  ⚠️  RSS 解析失敗：{e}")
        return []

    # 頻道層級元資料（用於 prompt 注入，提升人名/專有名詞辨識精確度）
    feed_title = feed.feed.get("title", "").strip()
    feed_author = feed.feed.get("author", feed.feed.get("itunes_author", "")).strip()

    episodes = []
    for entry in feed.entries:
        guid = entry.get("id") or entry.get("link", "")
        if not guid:
            continue
        audio_url = _extract_audio_url(entry)
        if not audio_url:
            continue
        episodes.append({
            "guid": guid,
            "title": entry.get("title", "未知集數"),
            "audio_url": audio_url,
            "published": entry.get("published", ""),
            "rss_url": rss_url,
            "feed_title": feed_title,
            "feed_author": feed_author,
        })

    if not episodes:
        return []

    if mode == "latest":
        if episode_number:
            # 在 title 中搜尋符合集數編號的集數
            matched = [
                ep for ep in episodes
                if episode_number in ep["title"].replace(" ", "")
                or f"EP{episode_number}" in ep["title"].upper()
                or f"EP {episode_number}" in ep["title"].upper()
                or f"第{episode_number}集" in ep["title"]
            ]
            if matched:
                print(f"  [OK] 找到集數 {episode_number}：{matched[0]['title']}")
                return [matched[0]]
            print(f"  [WARN] 找不到集數 {episode_number}（RSS 僅包含最近 {len(episodes)} 集），改取最新一集")

        elif apple_hint:
            # Apple 單集 URL：優先以發布日期比對，其次以 slug 關鍵字比對
            if apple_hint["date"]:
                date_matched = [
                    ep for ep in episodes
                    if apple_hint["date"] in format_rss_date(ep["published"])
                ]
                if date_matched:
                    print(f"  [OK] Apple 單集 URL 日期比對成功 {apple_hint['date']}：{date_matched[0]['title']}")
                    return [date_matched[0]]

            # 日期比對失敗，改用 slug 關鍵字（取前 5 個非空 token）
            slug_tokens = [t for t in apple_hint["slug"].split("-") if len(t) > 1][:5]
            for ep in episodes:
                if any(tok in ep["title"] for tok in slug_tokens):
                    print(f"  [OK] Apple 單集 URL 關鍵字比對成功：{ep['title']}")
                    return [ep]

            print(f"  [WARN] Apple 單集 URL 無法比對到對應集數，改取最新一集")

        return [episodes[0]]

    # daily：以 (rss_url, chat_id) 為複合 key 去重
    new = [ep for ep in episodes if not is_processed(rss_url, ep["guid"], chat_id)]
    print(f"  ✅ 新集數：{len(new)} / {len(episodes)}")
    return new


def _extract_audio_url(entry) -> str | None:
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("audio"):
            return enc.get("href") or enc.get("url")
    for link in getattr(entry, "links", []):
        if link.get("type", "").startswith("audio"):
            return link.get("href")
    return None


# ── 音檔下載 + 壓縮 ─────────────────────────────────────────────────────────

def compress_audio(src_path: str) -> str:
    """
    用 ffmpeg 把音檔壓縮成 32kbps mono 16kHz MP3（僅用於語音辨識，音質夠用）。
    典型節省：128kbps stereo 60MB → 32kbps mono ~15MB（4x 縮小）。
    若 ffmpeg 不存在，直接回傳原路徑。
    """
    if not shutil.which("ffmpeg"):
        print("  ℹ️  ffmpeg 未安裝，跳過壓縮步驟")
        return src_path

    compressed = src_path.replace(".mp3", "_c.mp3").replace(".m4a", "_c.mp3")
    cmd = [
        "ffmpeg", "-y", "-i", src_path,
        "-ac", "1",          # 單聲道
        "-ar", "16000",      # 16kHz（語音辨識標準取樣率）
        "-b:a", "32k",       # 32kbps 夠 NLM 辨識
        "-map_metadata", "-1",  # 不帶 metadata，減少檔案
        "-loglevel", "error",
        compressed,
    ]
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    elapsed = time.time() - t0

    if result.returncode == 0 and os.path.exists(compressed):
        orig_mb = os.path.getsize(src_path) / (1024 * 1024)
        comp_mb = os.path.getsize(compressed) / (1024 * 1024)
        ratio = (1 - comp_mb / orig_mb) * 100 if orig_mb > 0 else 0
        print(f"  🗜️  壓縮完成：{orig_mb:.1f}MB → {comp_mb:.1f}MB (-{ratio:.0f}%) [{elapsed:.0f}s]")
        os.remove(src_path)   # 刪掉原始大檔
        return compressed
    else:
        print(f"  ⚠️  ffmpeg 壓縮失敗，使用原始檔：{result.stderr[:200]}")
        return src_path


def download_audio(audio_url: str, title: str, max_retries: int = 2) -> str | None:
    """
    下載音檔到暫存檔後立即壓縮（ffmpeg 可用時）。
    失敗最多重試 max_retries 次，間隔 10 秒。
    """
    suffix = ".m4a" if "m4a" in audio_url.lower() else ".mp3"
    for attempt in range(1, max_retries + 2):  # 1 .. max_retries+1
        label = f" (第 {attempt} 次嘗試)" if attempt > 1 else ""
        print(f"  ⬇️  下載音檔：{title}{label}")
        t0 = time.time()
        try:
            resp = requests.get(audio_url, timeout=DOWNLOAD_TIMEOUT_SEC, stream=True)
            resp.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp_path = tmp.name
                size_mb = 0
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    tmp.write(chunk)
                    size_mb += len(chunk) / (1024 * 1024)
                    if size_mb > MP3_SIZE_LIMIT_MB:
                        os.remove(tmp_path)
                        print(f"  ⚠️  超過 {MP3_SIZE_LIMIT_MB}MB，跳過")
                        return None
            elapsed = time.time() - t0
            print(f"  ✅ 下載完成：{size_mb:.1f}MB [{elapsed:.0f}s]")
            # 立即壓縮，減少 NLM 上傳時間
            return compress_audio(tmp_path)
        except Exception as e:
            print(f"  ❌ 下載失敗：{e}")
            if attempt <= max_retries:
                print("     10 秒後重試...")
                time.sleep(10)
    return None



# ── NLM 分析 ──────────────────────────────────────────────────────────────

def analyze_with_nlm(runner: NotebookRunner, mp3_path: str, prompt: str) -> str | None:
    with NotebookSession(runner, "POD") as session:
        if not session.ready():
            print("  ❌ 無法建立 NotebookLM notebook")
            return None
        print(f"  📓 Notebook：{session.notebook_id}")
        print("  ⏳ 上傳音檔等待轉錄...")
        t0 = time.time()
        result = runner.run(
            "source", "add", session.notebook_id,
            "--file", mp3_path, "--wait", verbose=True,
        )
        if result.returncode != 0:
            print(f"  ❌ 上傳失敗：{result.stderr}")
            return None
        print(f"  ✅ 轉錄完成 [{time.time()-t0:.0f}s]，開始 query...")
        t1 = time.time()
        qr = runner.run("query", "notebook", session.notebook_id, prompt)
        if qr.returncode != 0:
            print(f"  ❌ query 失敗：{qr.stderr}")
            return None
        print(f"  ✅ Query 完成 [{time.time()-t1:.0f}s]")
        return parse_query_output(qr.stdout)



# ── 推送：HTML 報告 + Redis 連結 ────────────────────────────────

def send_podcast_report(
    title: str,
    analysis: str,
    published: str,
    label: str = "Podcast",
    chat_id: str = "",
    message_id: str = "",
) -> bool:
    """
    將分析文字生成精美 HTML 報告，存入 Redis，發送 TG 摘要 + 連結。
    若 Redis 未設定，則 fallback 為純文字推送（誅於 4096 字）。
    """
    target_chat = chat_id or Config.TG_CHAT_ID
    if not target_chat:
        print("  ⚠️  未設定 TG 憑證，跳過")
        return False

    # 將 pending 訊息刪除
    if message_id:
        Notifier.delete_pending_message(target_chat, message_id)

    # 摘要文字（前 200 字）與日期解析
    import re as _re
    clean = _re.sub(r"【.*?】", "", analysis).strip()
    preview = (clean[:200] + "…") if len(clean) > 200 else clean

    # 正確解析 RSS 日期（RFC 2822 → YYYY-MM-DD）
    ep_date = format_rss_date(published)

    # 生成 HTML 報告
    print("  🎨 生成 HTML 報告...")
    html_content = generate_podcast_html_report(
        ep_title=title,
        ep_date=ep_date,
        channel_label=label,
        analysis=analysis,
    )

    # 嘗試發送 HTML 報告連結
    # 各欄位分開傳入，由 service.py 內部做 html_escape，防止標題特殊字元破壞解析
    print(f"  🔍 Redis 狀態：URL={bool(Config.REDIS_URL)} TOKEN={bool(Config.REDIS_TOKEN)}")
    success = Notifier.send_report_link(
        target_chat,
        html_content,
        "",          # caption 留空，改用下方具名欄位
        label=label,
        title=title,
        ep_date=ep_date,
        preview=preview,
    )
    if success:
        print("  ✅ HTML 報告推送成功")
        return True

    # Fallback：Redis 未設定，改用分段純文字
    print("  ⚠️  Redis 未設定 (UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN 未配置)")
    print("  ⚠️  改用純文字推送（設定 GitHub Secrets 即可解鎖 HTML 報告連結功能）")
    # 完整分析文字，不再限制 200 字
    header = f"🎙️ {label} 財經分析\n📌 {title}\n📅 {ep_date}\n\n"
    body = analysis if len(header + analysis) <= 4096 else analysis[:4090 - len(header)] + "…"
    return Notifier.send_text(target_chat, header + body, html=False)





# ── 主流程 ────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 55)
    print("🎙️  Podcast 財經分析掃描器")
    print("=" * 55)

    if not AuthManager.deploy_credentials():
        print("❌ NLM 憑證初始化失敗")
        sys.exit(1)

    init_empty()

    mode = os.environ.get("PODCAST_MODE", "daily")
    on_demand_chat = os.environ.get("PODCAST_CHAT_ID", "")
    on_demand_msg = os.environ.get("PODCAST_MESSAGE_ID", "")
    episode_number = os.environ.get("PODCAST_EPISODE_NUMBER", "").strip()  # e.g. "655"
    prompt_key = os.environ.get("CUSTOM_PROMPT", "podcast")  # 預設使用 podcast 專屬 prompt
    prompt = get_nlm_prompt(prompt_key)
    print(f"📝 模式：{mode}  Prompt：{prompt_key}  集數：{episode_number or '最新'}")

    # RSS 來源優先順序：
    #   1. PODCAST_RSS_URLS 環境變數（on-demand 單次查詢）
    #   2. WEBSITE_KOLS_FILE（網站專屬 KOL 清單，daily scanner 使用）
    #   3. processed_podcasts.json 訂閱清單（TG /subpodcast 訂閱）
    rss_env = os.environ.get("PODCAST_RSS_URLS", "").strip()
    website_kols_file = os.environ.get("WEBSITE_KOLS_FILE", "").strip()

    if rss_env:
        rss_sources = [(u.strip(), "") for u in rss_env.split(",") if u.strip()]
    elif website_kols_file and Path(website_kols_file).exists():
        import json as _json
        try:
            kols = _json.loads(Path(website_kols_file).read_text(encoding="utf-8"))
            rss_sources = [(k["rss_url"], k.get("label", "")) for k in kols if k.get("rss_url")]
            print(f"📋 網站 KOL 清單：{len(rss_sources)} 個頻道（{website_kols_file}）")
        except Exception as e:
            print(f"⚠️  無法讀取 {website_kols_file}：{e}，改用訂閱清單")
            rss_sources = []
    else:
        rss_sources = []

    if not rss_sources:
        subs = get_subscriptions()
        if subs:
            rss_sources = [(url, info.get("label", "")) for url, info in subs.items()]
        else:
            print("ℹ️  無 RSS 來源且無訂閱清單，結束。")
            print("   使用 /subpodcast <url> 訂閱後即可自動推送。")
            return

    runner = NotebookRunner()
    total_success = 0
    error_msg = ""   # 最後一個錯誤訊息，供安全網使用

    for rss_url, label in rss_sources:
        episodes = fetch_new_episodes(
            rss_url, mode=mode, chat_id=on_demand_chat, episode_number=episode_number
        )
        if not episodes:
            msg = f"🔚 [{label or rss_url[:40]}] 無新集數"
            print(msg)
            if on_demand_chat and mode == "latest":
                # on-demand 模式：找不到集數也要告知用戶
                if episode_number:
                    error_msg = f"⚠️ 找不到第 {episode_number} 集，請確認集數是否正確。"
                else:
                    error_msg = "⚠️ 此 Podcast 目前沒有可分析的新集數。"
            continue

        to_process = episodes[:1] if mode == "latest" else episodes[:MAX_EPISODES_PER_RUN]

        for ep in to_process:
            print(f"\n{'─' * 50}")
            print(f"📻 {ep['title']}  [{ep['published']}]")
            mp3_path = None
            try:
                cached_analysis = get_cached_analysis(rss_url, ep["guid"], prompt_key)
                if cached_analysis:
                    print("  ⚡ 命中 Podcast 分析快取，跳過下載與 NotebookLM")
                    send_podcast_report(
                        title=ep["title"],
                        analysis=cached_analysis,
                        published=ep["published"],
                        label=label or "Podcast",
                        chat_id=on_demand_chat,
                        message_id=on_demand_msg,
                    )
                    on_demand_msg = ""
                    error_msg = ""
                    if mode == "daily":
                        mark_processed(rss_url, ep["guid"], chat_id=on_demand_chat)
                    total_success += 1
                    continue

                mp3_path = download_audio(ep["audio_url"], ep["title"])
                if not mp3_path:
                    error_msg = f"❌ 音檔下載失敗：{ep['title'][:60]}"
                    print(f"  {error_msg}")
                    continue

                # 將 RSS 元資料（頻道名、主持人、集數標題）注入 prompt 開頭，
                # 讓 NLM 能以正確的人名與專有名詞作為轉錄修正參考，通用於所有頻道。
                ep_prompt = _build_episode_prompt(prompt, ep)

                analysis = analyze_with_nlm(runner, mp3_path, ep_prompt)
                if not analysis:
                    error_msg = f"❌ AI 分析失敗（NLM 無回應），請稍後再試。\n集數：{ep['title'][:60]}"
                    print("  ❌ NLM 分析失敗")
                    continue

                if set_cached_analysis(rss_url, ep["guid"], prompt_key, analysis):
                    print(f"  💾 已寫入 Podcast 分析快取（TTL {Config.REDIS_PODCAST_TTL}s）")

                # 寫入 Neon DB（僅 daily 模式，on-demand 不存 DB）
                if mode == "daily":
                    ep_summary, ep_stocks, ep_sentiment = _parse_nlm_analysis(analysis)
                    print(f"  [PARSE] sentiment={ep_sentiment} stocks={ep_stocks[:5]}")
                    _db_kol_id = ensure_kol(rss_url, label or "")
                    # summary 存完整分析文字，讓詳細頁面能顯示完整報告
                    write_episode(
                        kol_id=_db_kol_id,
                        guid=ep["guid"],
                        title=ep["title"],
                        published_str=format_rss_date(ep["published"]),
                        summary=analysis,
                        sentiment=ep_sentiment,
                        stocks_mentioned=ep_stocks,
                        report_url="",
                    )

                send_podcast_report(
                    title=ep["title"],
                    analysis=analysis,
                    published=ep["published"],
                    label=label or "Podcast",
                    chat_id=on_demand_chat,
                    message_id=on_demand_msg,
                )
                on_demand_msg = ""  # 已刪，避免安全網重複刪
                error_msg = ""      # 成功，清除錯誤狀態

                if mode == "daily":
                    mark_processed(rss_url, ep["guid"], chat_id=on_demand_chat)
                total_success += 1

            except Exception as e:
                error_msg = f"❌ 系統例外：{str(e)[:100]}"
                print(f"  ❌ 例外：{e}")
            finally:
                if mp3_path and os.path.exists(mp3_path):
                    os.remove(mp3_path)

            if ep != to_process[-1]:
                time.sleep(30)

    print(f"\n{'=' * 55}")
    print(f"✨ 完成：成功 {total_success} 集")
    print("=" * 55)

    # Daily 模式：更新共識儀表板
    if mode == "daily" and total_success > 0:
        print("\n📊 更新 Neon DB 共識指標...")
        compute_and_write_consensus()

    # 安全網：確保 on-demand 用戶一定收到回應
    # 若成功推送，on_demand_msg 已在 send_podcast_report 內刪除（置空）
    # 若失敗，這裡發送錯誤通知（同時替換掉 pending 訊息）
    if on_demand_chat and on_demand_msg:
        bot_token = Config.TG_BOT_TOKEN
        if bot_token:
            # 先刪 pending 訊息
            try:
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/deleteMessage",
                    json={"chat_id": on_demand_chat, "message_id": int(on_demand_msg)},
                    timeout=10,
                )
            except Exception:
                pass
            # 再發錯誤通知
            notice = error_msg or "⚠️ 分析未能完成，可能原因：音檔下載失敗 / AI 服務暫時無法使用。\n請稍後再試，或嘗試其他集數。"
            try:
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": on_demand_chat,
                        "text": f"🎙️ Podcast 分析結果\n\n{notice}",
                        "parse_mode": "HTML",
                    },
                    timeout=10,
                )
            except Exception:
                pass



if __name__ == "__main__":
    main()
