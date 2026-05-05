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
from datetime import date, timedelta
from pathlib import Path

import feedparser
import requests

# ── 確保 project root 在 path ──────────────────────────────────────────────
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.auth import AuthManager
from app.config import Config
from app.db_writer import (
    compute_and_write_consensus,
    episode_exists,
    ensure_analytics_schema,
    ensure_kol,
    finish_job_item,
    finish_job_run,
    start_job_item,
    start_job_run,
    migrate_legacy_kol_aliases,
    write_episode,
)
from app.notebook.notebook_session import NotebookSession
from app.notebook.parsing import parse_query_output
from app.notebook.runner import NotebookRunner
from app.notebook.source_loader import SourceLoader
from app.notifier.reporting import generate_podcast_html_report
from app.notifier.service import Notifier
from app.podcast_cache import get_cached_analysis, set_cached_analysis
from app.podcast_state import get_subscriptions, init_empty, is_processed, mark_processed
from api.utils.prompt_manager import get_nlm_prompt

MAX_EPISODES_PER_RUN = 2
MAX_DAILY_FEED_ITEMS = int(os.environ.get("PODCAST_MAX_DAILY_FEED_ITEMS", "12"))
DAILY_FRESHNESS_DAYS = int(os.environ.get("PODCAST_DAILY_FRESHNESS_DAYS", "2"))
DAILY_DIGEST_LOOKBACK_DAYS = int(os.environ.get("PODCAST_DAILY_DIGEST_LOOKBACK_DAYS", "1"))
DOWNLOAD_TIMEOUT_SEC = 300
MP3_SIZE_LIMIT_MB = 200

ARTICLE_INCLUDE_KEYWORDS = {
    "ai", "人工智慧", "生成式", "agent", "代理", "openai", "chatgpt",
    "google", "alphabet", "gemini", "microsoft", "微軟", "amazon", "aws",
    "meta", "apple", "tesla", "oracle", "甲骨文", "nvidia", "輝達",
    "amd", "tsmc", "台積電", "半導體", "晶片", "gpu", "hbm", "dram",
    "nand", "記憶體", "伺服器", "資料中心", "雲端", "資安", "機器人",
    "電動車", "供應鏈", "財報", "營收", "獲利", "股價", "ipo", "併購",
    "資本市場", "投資", "市場", "產業", "商機", "新創", "venture",
}

ARTICLE_EXCLUDE_KEYWORDS = {
    "mbti", "星座", "職涯", "職場", "履歷", "面試", "加薪", "升官",
    "主管", "總經理", "管理術", "心理測驗", "旅遊", "美食", "影劇",
    "巴爾幹", "波士尼亞", "能源協議", "軍事", "戰爭", "國防協議",
}


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _should_send_podcast_report(mode: str, chat_id: str) -> bool:
    if chat_id:
        return True
    if mode == "daily":
        return _env_flag("PODCAST_SEND_TELEGRAM_DAILY", False)
    return True


def _should_send_daily_digest(mode: str, chat_id: str) -> bool:
    return mode == "daily" and not chat_id and _env_flag("PODCAST_SEND_DAILY_DIGEST", True)


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


def _build_article_prompt(ep: dict) -> str:
    lines = []
    if ep.get("feed_title"):
        lines.append(f"來源名稱：{ep['feed_title']}")
    if ep.get("feed_author"):
        lines.append(f"作者/媒體：{ep['feed_author']}")
    if ep.get("title"):
        lines.append(f"文章標題：{ep['title']}")
    if ep.get("content_url"):
        lines.append(f"文章 URL：{ep['content_url']}")

    context = "【來源背景資訊】\n" + "\n".join(lines)
    task = (
        "你是一位專業的台灣科技、商業與財經研究助理。"
        "請把此來源整理成可供投研首頁使用的語言訊號，全程使用台灣繁體中文。\n\n"
        "【文字紀錄】\n"
        "請用 3-6 段整理文章核心內容，保留原文觀點、產業語氣與重要脈絡；"
        "不要寫成逐字稿，不要加入沒有來源支持的推論。\n\n"
        "【投資倒數小結】\n"
        "1. 台美股焦點標的：列出文中提到的台股、美股代號或公司名，一行一個，附上文章觀點。"
        "若沒有明確上市標的，請寫「無明確上市標的」；不要把 GEO、RFID、CNC、MBTI 等概念、技術或人格縮寫當成股票代號。\n"
        "2. 本集結論：用 2-3 句話總結此來源對科技、商業或市場趨勢的核心訊號。\n\n"
        "【重要規範：直接輸出兩個段落，嚴禁包含思考過程。嚴禁使用 Markdown 加粗（** 或 __）。】"
    )
    return f"{context}\n\n{task}"


def _fallback_article_analysis(ep: dict) -> str:
    title = str(ep.get("title") or "未命名文章")
    source = str(ep.get("feed_title") or "RSS 來源")
    excerpt = str(ep.get("entry_summary") or "").strip()
    if not excerpt:
        excerpt = "RSS 未提供足夠摘要，僅保留標題作為低信心待追蹤訊號。"
    return (
        "【文字紀錄】\n"
        f"{source} 發布「{title}」。{excerpt}\n\n"
        "【投資倒數小結】\n"
        "1. 台美股焦點標的：無明確上市標的。\n"
        f"2. 本集結論：此來源因 NotebookLM query timeout，先以 RSS 摘要保留為低信心觀察訊號；後續可由下一次掃描或人工詳讀補強。"
    )


def _parse_nlm_analysis(analysis: str) -> tuple[str, list[str], str]:
    """
    從 NLM podcast prompt 的分析結果中提取結構化資料：
    - summary  : 用於 DB 摘要欄（完整 analysis 原文）
    - stocks   : 提及的股票代碼列表（台股 4 碼 + 美股大寫）
    - sentiment: 'bullish' | 'bearish' | 'neutral'

    同時相容新格式（【個股觀點】＋【市場總結與操作建議】）
    與舊格式（【投資倒數小結】）。
    """
    skip_tickers = {
        'AI', 'IT', 'US', 'TW', 'Q1', 'Q2', 'Q3', 'Q4',
        'EPS', 'ETF', 'PE', 'PB', 'EV', 'IPO', 'RSI', 'MA',
        'CEO', 'CFO', 'GDP', 'CPI', 'PCE', 'FED', 'ECB',
        'GEO', 'CNC', 'RFID', 'HID', 'ASSA', 'ABLOY', 'NFC',
    }

    stocks: list[str] = []

    # ── 新格式：從【個股觀點】提取代號（每行第一欄，以｜分隔）────────────
    stock_section_new = re.search(r'【個股觀點】\s*([\s\S]*?)(?=\n【|$)', analysis)
    if stock_section_new:
        for line in stock_section_new.group(1).strip().splitlines():
            parts = line.split('｜')
            if len(parts) >= 2:
                ticker = parts[0].strip()
                if re.match(r'^\d{4}$', ticker):
                    stocks.append(ticker)
                elif re.match(r'^[A-Z]{2,5}$', ticker) and ticker not in skip_tickers:
                    stocks.append(ticker)

    # ── 舊格式 fallback：從【投資倒數小結】提取 ─────────────────────────
    if not stocks:
        m3 = re.search(r'1[．.、]\s*台美股焦點標的[：:](.*?)(?=2[．.、]|\Z)', analysis, re.DOTALL)
        if m3:
            section = m3.group(1)
            tw = re.findall(r'\b(\d{4})\b', section)
            us = re.findall(r'\b([A-Z]{2,5})\b', section)
            stocks = list(dict.fromkeys(tw + [t for t in us if t not in skip_tickers]))

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
        "AWS": "AMZN", "甲骨文": "ORCL", "甲骨文公司": "ORCL",
        "Salesforce": "CRM", "Adobe": "ADBE",
    }
    for cn, ticker in cn_map.items():
        if cn in analysis and ticker not in stocks:
            stocks.append(ticker)

    # ── 摘要：供 DB 顯示用，優先取【市場總結】，fallback 取前 400 字 ──────
    summary_section = re.search(r'【市場總結與操作建議】\s*([\s\S]*?)(?=\n【|$)', analysis)
    if summary_section:
        summary = summary_section.group(1).strip()[:600]
    else:
        # 舊格式：取「本集結論」
        m_sum = re.search(r'2[．.、]\s*本集結論[：:]\s*(.*?)(?=\n\n|\Z)', analysis, re.DOTALL)
        summary = m_sum.group(1).strip() if m_sum else analysis[:400].strip()

    # ── 情緒判斷：正負關鍵詞計分 ─────────────────────────────────────────
    bullish_kw = ['看多', '偏多', '樂觀', '買進', '做多', '突破', '強勢',
                  '利多', '長多', '看好', '正向', '走強', '上攻', '偏樂',
                  '多方看好', '做多布局', '拉回買', '回測買', '強攻']
    bearish_kw = ['看空', '偏空', '謹慎', '賣出', '做空', '回檔', '壓力',
                  '利空', '下跌', '危險', '風險高', '弱勢', '偏保守', '下行',
                  '空方謹慎', '減碼', '停損', '出場觀望']
    bull = sum(analysis.count(w) for w in bullish_kw)
    bear = sum(analysis.count(w) for w in bearish_kw)
    if bull > bear + 2:
        sentiment = 'bullish'
    elif bear > bull + 2:
        sentiment = 'bearish'
    else:
        sentiment = 'neutral'

    return summary, stocks, sentiment


def _extract_analysis_section(text: str, header: str) -> str:
    m = re.search(rf"【{re.escape(header)}】\s*([\s\S]*?)(?=\n【|$)", text)
    return m.group(1).strip() if m else ""


def _strip_analysis_citations(text: str) -> str:
    return re.sub(r"\s*\[\d+(?:[,，\s\-–]+\d+)*\]", "", text).strip()


def _digest_item_summary(analysis: str) -> str:
    summary = _extract_analysis_section(analysis, "投資倒數小結")
    conclusion = ""
    if summary:
        cm = re.search(r"本集結論[：:]\s*(.*?)$", summary, re.DOTALL)
        conclusion = cm.group(1).strip() if cm else summary
    if not conclusion:
        conclusion = _extract_analysis_section(analysis, "市場總結與操作建議")
    if not conclusion:
        clean = re.sub(r"【.*?】", "", analysis).strip()
        conclusion = clean[:360]
    return _strip_analysis_citations(re.sub(r"\s+", " ", conclusion))[:420]


def _sentiment_label(sentiment: str) -> str:
    return {
        "bullish": "偏多",
        "bearish": "偏空",
        "neutral": "中性",
    }.get(sentiment, "中性")


def _build_daily_digest_candidate(kol_meta: dict, ep: dict, analysis: str) -> dict | None:
    if not _is_in_daily_digest_window(ep):
        return None
    _, stocks, sentiment = _parse_nlm_analysis(analysis)
    return {
        "label": kol_meta.get("label") or ep.get("feed_title") or "Podcast",
        "title": ep.get("title") or "未命名集數",
        "published": format_rss_date(ep.get("published", "")),
        "stocks": stocks,
        "sentiment": sentiment,
        "summary": _digest_item_summary(analysis),
    }


def build_daily_investment_digest(items: list[dict]) -> str:
    if not items:
        return ""

    generated_at = time.strftime("%Y-%m-%d %H:%M")
    stock_sources: dict[str, list[str]] = {}
    for item in items:
        for stock in item.get("stocks", []):
            stock_sources.setdefault(stock, [])
            label = item.get("label", "Podcast")
            if label not in stock_sources[stock]:
                stock_sources[stock].append(label)

    sentiment_counts = {"bullish": 0, "bearish": 0, "neutral": 0}
    for item in items:
        sentiment = item.get("sentiment", "neutral")
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

    lines = [
        "# 每日 Podcast 投資統整",
        "",
        f"產生時間：{generated_at}",
        f"掃描範圍：近 {DAILY_DIGEST_LOOKBACK_DAYS} 天成功完成分析的 podcast / 文章來源",
        f"本次納入：{len(items)} 則訊號",
        "",
        "## 今日重點",
        (
            f"- 情緒分布：偏多 {sentiment_counts.get('bullish', 0)}、"
            f"中性 {sentiment_counts.get('neutral', 0)}、偏空 {sentiment_counts.get('bearish', 0)}"
        ),
        f"- 焦點標的：{', '.join(stock_sources.keys()) if stock_sources else '本輪未抽出明確台美股標的'}",
        "",
        "## 焦點標的",
    ]

    if stock_sources:
        for stock, sources in stock_sources.items():
            lines.append(f"- {stock}：{', '.join(sources)}")
    else:
        lines.append("- 無明確上市標的")

    lines.extend(["", "## 逐集訊號"])
    for item in items:
        stocks = ", ".join(item.get("stocks", [])) or "無明確標的"
        lines.extend([
            "",
            f"### {item.get('label', 'Podcast')}｜{item.get('title', '未命名集數')}",
            "",
            f"- 日期：{item.get('published') or '未知'}",
            f"- 情緒：{_sentiment_label(item.get('sentiment', 'neutral'))}",
            f"- 標的：{stocks}",
            "",
            item.get("summary") or "未取得摘要。",
        ])

    lines.extend([
        "",
        "## 風險提醒",
        "",
        "以上內容為 Podcast 與 RSS 來源的 AI 統整，只供研究追蹤，不構成投資建議。",
    ])
    return "\n".join(lines)


def _daily_digest_metrics(items: list[dict]) -> tuple[dict[str, int], dict[str, list[str]]]:
    sentiment_counts = {"bullish": 0, "bearish": 0, "neutral": 0}
    stock_sources: dict[str, list[str]] = {}
    for item in items:
        sentiment = item.get("sentiment", "neutral")
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        for stock in item.get("stocks", []):
            stock_sources.setdefault(stock, [])
            label = item.get("label", "Podcast")
            if label not in stock_sources[stock]:
                stock_sources[stock].append(label)
    return sentiment_counts, stock_sources


def build_daily_investment_digest_caption(items: list[dict]) -> str:
    if not items:
        return ""
    sentiment_counts, stock_sources = _daily_digest_metrics(items)
    top_stocks = ", ".join(list(stock_sources.keys())[:8]) or "無明確上市標的"
    first_summary = items[0].get("summary", "本輪未取得摘要。")
    if len(first_summary) > 180:
        first_summary = first_summary[:177] + "..."
    return (
        "🔎 研究完成：每日 Podcast 投資統整\n\n"
        "📝 核心結論：\n"
        f"本次納入 {len(items)} 則近一天訊號；"
        f"情緒分布為偏多 {sentiment_counts.get('bullish', 0)}、"
        f"中性 {sentiment_counts.get('neutral', 0)}、偏空 {sentiment_counts.get('bearish', 0)}。\n"
        f"焦點標的：{top_stocks}\n\n"
        f"{first_summary}"
    )


def generate_daily_investment_html_report(items: list[dict]) -> str:
    sentiment_counts, stock_sources = _daily_digest_metrics(items)
    generated_at = time.strftime("%Y-%m-%d %H:%M")
    total = len(items)
    stock_count = len(stock_sources)
    top_stocks = list(stock_sources.items())[:12]

    def esc(value: object) -> str:
        text = str(value or "")
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def pct(count: int) -> str:
        return f"{round(count / total * 100):.0f}%" if total else "0%"

    def sentiment_class(sentiment: str) -> str:
        return {
            "bullish": "bullish",
            "bearish": "bearish",
            "neutral": "neutral",
        }.get(sentiment, "neutral")

    stock_rows = "\n".join(
        f"""
        <tr>
          <td><span class="ticker">{esc(stock)}</span></td>
          <td>{len(sources)}</td>
          <td>{esc(", ".join(sources))}</td>
        </tr>
        """
        for stock, sources in top_stocks
    ) or '<tr><td colspan="3" class="muted">本輪未抽出明確台美股標的</td></tr>'

    source_cards = "\n".join(
        f"""
        <article class="source-card">
          <div class="source-topline">
            <span>{esc(item.get("label", "Podcast"))}</span>
            <span>{esc(item.get("published") or "未知日期")}</span>
          </div>
          <h3>{esc(item.get("title", "未命名集數"))}</h3>
          <div class="source-meta">
            <span class="pill {sentiment_class(item.get("sentiment", "neutral"))}">{esc(_sentiment_label(item.get("sentiment", "neutral")))}</span>
            <span>{esc(", ".join(item.get("stocks", [])) or "無明確標的")}</span>
          </div>
          <p>{esc(item.get("summary") or "未取得摘要。")}</p>
        </article>
        """
        for item in items
    )

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>每日 Podcast 投資統整</title>
  <style>
    :root {{
      --ink: #111827;
      --muted: #667085;
      --line: #d9e2ec;
      --paper: #f6f8fb;
      --card: #ffffff;
      --blue: #1455d9;
      --green: #047857;
      --red: #b42318;
      --amber: #b54708;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC", Arial, sans-serif;
      line-height: 1.65;
    }}
    .report {{ max-width: 1120px; margin: 0 auto; padding: 36px 20px 64px; }}
    header {{
      padding: 30px 0 22px;
      border-bottom: 3px solid var(--ink);
      display: grid;
      gap: 10px;
    }}
    .eyebrow {{ color: var(--blue); font-size: 0.78rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }}
    h1 {{ margin: 0; font-size: clamp(1.8rem, 4vw, 3rem); line-height: 1.15; letter-spacing: 0; }}
    .subtitle {{ max-width: 760px; color: var(--muted); margin: 0; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 16px; color: var(--muted); font-size: .9rem; }}
    .kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 24px 0; }}
    .kpi {{ background: var(--card); border: 1px solid var(--line); padding: 18px; border-radius: 8px; }}
    .kpi .label {{ color: var(--muted); font-size: .78rem; font-weight: 700; }}
    .kpi .value {{ font-size: 1.65rem; font-weight: 800; margin-top: 6px; }}
    section {{ margin-top: 28px; }}
    h2 {{ font-size: 1.1rem; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--line); }}
    .grid {{ display: grid; grid-template-columns: 1.1fr .9fr; gap: 18px; align-items: start; }}
    .panel {{ background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 20px; }}
    .bars {{ display: grid; gap: 12px; }}
    .bar-row {{ display: grid; grid-template-columns: 56px 1fr 48px; align-items: center; gap: 10px; font-size: .9rem; }}
    .bar-track {{ height: 10px; background: #edf2f7; border-radius: 999px; overflow: hidden; }}
    .bar-fill {{ height: 100%; background: var(--blue); }}
    table {{ width: 100%; border-collapse: collapse; font-size: .92rem; }}
    th, td {{ padding: 11px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: .76rem; text-transform: uppercase; letter-spacing: .08em; }}
    .ticker {{ font-weight: 800; color: var(--blue); }}
    .source-list {{ display: grid; gap: 14px; }}
    .source-card {{ background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 18px; }}
    .source-topline {{ display: flex; justify-content: space-between; gap: 12px; color: var(--muted); font-size: .8rem; font-weight: 700; }}
    .source-card h3 {{ margin: 8px 0; font-size: 1rem; line-height: 1.4; }}
    .source-card p {{ margin: 12px 0 0; color: #344054; }}
    .source-meta {{ display: flex; flex-wrap: wrap; gap: 8px; color: var(--muted); font-size: .85rem; }}
    .pill {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 2px 9px; font-weight: 800; }}
    .pill.bullish {{ color: var(--green); background: #ecfdf3; }}
    .pill.bearish {{ color: var(--red); background: #fef3f2; }}
    .pill.neutral {{ color: var(--amber); background: #fffaeb; }}
    .muted {{ color: var(--muted); }}
    footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--line); color: var(--muted); font-size: .82rem; }}
    @media (max-width: 760px) {{
      .kpis, .grid {{ grid-template-columns: 1fr; }}
      .report {{ padding: 24px 14px 48px; }}
    }}
  </style>
</head>
<body>
  <main class="report">
    <header>
      <div class="eyebrow">Daily Investment Brief</div>
      <h1>每日 Podcast 投資統整</h1>
      <p class="subtitle">彙整近 {DAILY_DIGEST_LOOKBACK_DAYS} 天成功完成分析的 Podcast 與 RSS 來源，萃取市場情緒、焦點標的與逐集投資訊號。</p>
      <div class="meta">
        <span>產生時間：{esc(generated_at)}</span>
        <span>資料來源：{total} 則訊號</span>
      </div>
    </header>

    <section class="kpis">
      <div class="kpi"><div class="label">納入訊號</div><div class="value">{total}</div></div>
      <div class="kpi"><div class="label">焦點標的</div><div class="value">{stock_count}</div></div>
      <div class="kpi"><div class="label">偏多比例</div><div class="value">{pct(sentiment_counts.get("bullish", 0))}</div></div>
      <div class="kpi"><div class="label">偏空比例</div><div class="value">{pct(sentiment_counts.get("bearish", 0))}</div></div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>市場情緒分布</h2>
        <div class="bars">
          <div class="bar-row"><span>偏多</span><div class="bar-track"><div class="bar-fill" style="width:{pct(sentiment_counts.get("bullish", 0))}"></div></div><strong>{sentiment_counts.get("bullish", 0)}</strong></div>
          <div class="bar-row"><span>中性</span><div class="bar-track"><div class="bar-fill" style="width:{pct(sentiment_counts.get("neutral", 0))}"></div></div><strong>{sentiment_counts.get("neutral", 0)}</strong></div>
          <div class="bar-row"><span>偏空</span><div class="bar-track"><div class="bar-fill" style="width:{pct(sentiment_counts.get("bearish", 0))}"></div></div><strong>{sentiment_counts.get("bearish", 0)}</strong></div>
        </div>
      </div>
      <div class="panel">
        <h2>焦點標的排行</h2>
        <table>
          <thead><tr><th>標的</th><th>提及</th><th>來源</th></tr></thead>
          <tbody>{stock_rows}</tbody>
        </table>
      </div>
    </section>

    <section>
      <h2>逐集投資訊號</h2>
      <div class="source-list">{source_cards}</div>
    </section>

    <footer>AI 統整僅供研究追蹤，不構成投資建議。請搭配原始來源、財報與風險承受度自行判斷。</footer>
  </main>
</body>
</html>"""


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


def _episode_published_date(ep: dict) -> date | None:
    published = format_rss_date(ep.get("published", ""))
    if not published:
        return None
    try:
        return date.fromisoformat(published[:10])
    except ValueError:
        return None


def _is_recent_daily_episode(ep: dict) -> bool:
    if DAILY_FRESHNESS_DAYS <= 0:
        return True
    published = _episode_published_date(ep)
    if not published:
        return False
    cutoff = date.today() - timedelta(days=DAILY_FRESHNESS_DAYS)
    return published >= cutoff


def _is_in_daily_digest_window(ep: dict) -> bool:
    if DAILY_DIGEST_LOOKBACK_DAYS <= 0:
        return True
    published = _episode_published_date(ep)
    if not published:
        return False
    cutoff = date.today() - timedelta(days=DAILY_DIGEST_LOOKBACK_DAYS)
    return published >= cutoff


def _entry_text(entry) -> str:
    fields = [
        entry.get("title", ""),
        entry.get("summary", ""),
        entry.get("description", ""),
    ]
    tags = getattr(entry, "tags", []) or []
    for tag in tags:
        term = tag.get("term") if isinstance(tag, dict) else ""
        if term:
            fields.append(term)
    return " ".join(str(field) for field in fields if field).lower()


def _clean_entry_summary(entry) -> str:
    raw = str(entry.get("summary", entry.get("description", "")) or "")
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]


def _is_research_article(entry, include_keywords: list[str] | None = None, exclude_keywords: list[str] | None = None) -> bool:
    text = _entry_text(entry)
    includes = {kw.lower() for kw in (include_keywords or [])} | ARTICLE_INCLUDE_KEYWORDS
    excludes = {kw.lower() for kw in (exclude_keywords or [])} | ARTICLE_EXCLUDE_KEYWORDS
    if any(kw and kw in text for kw in excludes):
        return False
    return any(kw and kw in text for kw in includes)


# ── RSS 掃描 ──────────────────────────────────────────────────────────────

def fetch_new_episodes(
    rss_url: str,
    mode: str = "daily",
    chat_id: str = "",
    episode_number: str = "",
    allow_text: bool = False,
    article_include_keywords: list[str] | None = None,
    article_exclude_keywords: list[str] | None = None,
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

    print(f"📡 掃描 RSS：{rss_url}")

    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        print(f"  ⚠️  RSS 解析失敗：{e}")
        return []

    # 頻道層級元資料（用於 prompt 注入，提升人名/專有名詞辨識精確度）
    feed_title = feed.feed.get("title", "").strip()
    feed_author = feed.feed.get("author", feed.feed.get("itunes_author", "")).strip()

    episodes = []
    entries = list(feed.entries)
    if mode == "daily" and MAX_DAILY_FEED_ITEMS > 0:
        entries = entries[:MAX_DAILY_FEED_ITEMS]

    for entry in entries:
        guid = entry.get("id") or entry.get("link", "")
        if not guid:
            continue
        audio_url = _extract_audio_url(entry)
        if not audio_url:
            if not allow_text or not entry.get("link"):
                continue
            if mode == "daily" and not _is_research_article(entry, article_include_keywords, article_exclude_keywords):
                continue
            episodes.append({
                "guid": guid,
                "title": entry.get("title", "未知文章"),
                "content_url": entry.get("link", ""),
                "published": entry.get("published", entry.get("updated", "")),
                "entry_summary": _clean_entry_summary(entry),
                "rss_url": rss_url,
                "feed_title": feed_title,
                "feed_author": feed_author,
                "source_kind": "article",
            })
            continue
        episodes.append({
            "guid": guid,
            "title": entry.get("title", "未知集數"),
            "audio_url": audio_url,
            "published": entry.get("published", ""),
            "rss_url": rss_url,
            "feed_title": feed_title,
            "feed_author": feed_author,
            "source_kind": "podcast",
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

    # Daily mode should stay fresh. If processed state is missing, do not backfill
    # older feed items into the website as if they were today's research.
    recent = [ep for ep in episodes if _is_recent_daily_episode(ep)]
    new = [ep for ep in recent if not is_processed(rss_url, ep["guid"], chat_id)]
    print(f"  New recent episodes: {len(new)} / {len(recent)} fresh / {len(episodes)} fetched")
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


def analyze_source_url_with_nlm(runner: NotebookRunner, url: str, prompt: str) -> str | None:
    with NotebookSession(runner, "WEB") as session:
        if not session.ready():
            print("  ❌ 無法建立 NotebookLM notebook")
            return None
        loader = SourceLoader(runner)
        print("  ⏳ 載入文章來源...")
        t0 = time.time()
        if not loader.add_source(session.notebook_id, url, wait=True):
            print("  ❌ 文章來源載入失敗")
            return None
        print(f"  ✅ 來源載入完成 [{time.time()-t0:.0f}s]，開始 query...")
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


def send_daily_investment_digest(items: list[dict]) -> bool:
    target_chat = Config.TG_CHAT_ID
    if not target_chat:
        print("  ⚠️  未設定 TELEGRAM_CHAT_ID，跳過每日統整報告")
        return False

    markdown_report = build_daily_investment_digest(items)
    if not markdown_report:
        print("  ℹ️  近一天沒有成功分析的 podcast 訊號，跳過每日統整報告")
        return False

    html_content = generate_daily_investment_html_report(items)
    caption = build_daily_investment_digest_caption(items)
    print("  📤 推送每日 Podcast 投資統整報告...")
    if Notifier.send_report_link(target_chat, html_content, caption):
        print("  ✅ 每日統整報告推送成功")
        return True

    print("  ⚠️  HTML 報告連結不可用，改用純文字推送每日統整")
    text = markdown_report if len(markdown_report) <= 4096 else markdown_report[:4093] + "..."
    return Notifier.send_text(target_chat, text, html=False)





# ── KOL metadata helpers ──────────────────────────────────────────────────

import hashlib as _hashlib
import json as _json


def _load_kol_registry(website_kols_file: str) -> dict[str, dict]:
    """
    Load website_kols.json and return a dict keyed by rss_url for O(1) lookup.
    Also returns entries with empty rss_url (keyed by kol_id) for registration.
    """
    if not website_kols_file or not Path(website_kols_file).exists():
        return {}
    try:
        kols = _json.loads(Path(website_kols_file).read_text(encoding="utf-8"))
        registry: dict[str, dict] = {}
        for k in kols:
            if k.get("rss_url"):
                registry[k["rss_url"]] = k
        return registry
    except Exception as e:
        print(f"⚠️  無法讀取 KOL registry：{e}")
        return {}


def _register_all_kols(website_kols_file: str) -> None:
    """Upsert metadata for ALL KOLs in website_kols.json — including those without RSS."""
    if not website_kols_file or not Path(website_kols_file).exists():
        return
    try:
        kols = _json.loads(Path(website_kols_file).read_text(encoding="utf-8"))
        for k in kols:
            if k.get("kol_id"):
                ensure_kol(k)
        migrated = migrate_legacy_kol_aliases(kols)
        if migrated:
            print(f"  [DB] migrated {migrated} legacy URL-name KOL episode rows")
    except Exception as e:
        print(f"⚠️  KOL metadata 注冊失敗：{e}")


def _build_kol_meta(rss_url: str, label: str, registry: dict[str, dict]) -> dict:
    """Return full KOL metadata from registry, or minimal fallback keyed by MD5."""
    if rss_url in registry:
        return registry[rss_url]
    return {
        "kol_id": _hashlib.md5(rss_url.encode()).hexdigest()[:10],
        "label": label or rss_url[:40],
        "host": "",
        "avatar": "🎙️",
        "color": "#6366f1",
        "rss_url": rss_url,
    }


def _write_episode_to_db(kol_meta: dict, ep: dict, analysis: str) -> bool:
    """Ensure KOL exists, parse analysis, write episode. Always called on success."""
    ep_summary, ep_stocks, ep_sentiment = _parse_nlm_analysis(analysis)
    print(f"  [DB] sentiment={ep_sentiment} stocks={ep_stocks[:5]}")
    kol_id = ensure_kol(kol_meta)
    return write_episode(
        kol_id=kol_id,
        guid=ep["guid"],
        title=ep["title"],
        published_str=format_rss_date(ep["published"]),
        summary=analysis,
        sentiment=ep_sentiment,
        stocks_mentioned=ep_stocks,
        report_url="",
    )


# ── 主流程 ────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 55)
    print("🎙️  Podcast 財經分析掃描器")
    print("=" * 55)

    if not AuthManager.deploy_credentials():
        print("❌ NLM 憑證初始化失敗")
        sys.exit(1)

    init_empty()
    ensure_analytics_schema()

    mode = os.environ.get("PODCAST_MODE", "daily")
    on_demand_chat = os.environ.get("PODCAST_CHAT_ID", "")
    on_demand_msg = os.environ.get("PODCAST_MESSAGE_ID", "")
    episode_number = os.environ.get("PODCAST_EPISODE_NUMBER", "").strip()
    prompt_key = os.environ.get("CUSTOM_PROMPT", "podcast")
    prompt = get_nlm_prompt(prompt_key)
    print(f"📝 模式：{mode}  Prompt：{prompt_key}  集數：{episode_number or '最新'}")

    website_kols_file = os.environ.get("WEBSITE_KOLS_FILE", "").strip()

    # 啟動時先把所有 KOL metadata 寫進 DB（含無 RSS 的 KOL）
    # 這是 SSOT 同步的核心步驟，確保網站顯示永遠跟 website_kols.json 一致
    if website_kols_file:
        _register_all_kols(website_kols_file)

    # 建立 rss_url → kol_meta 的查找表
    kol_registry = _load_kol_registry(website_kols_file)

    # RSS 來源優先順序：
    #   1. PODCAST_RSS_URLS 環境變數（on-demand 單次查詢）
    #   2. WEBSITE_KOLS_FILE 中有 rss_url 的 KOL（daily scanner）
    #   3. processed_podcasts.json 訂閱清單（TG /subpodcast）
    rss_env = os.environ.get("PODCAST_RSS_URLS", "").strip()

    if rss_env:
        rss_sources = [rss_url.strip() for rss_url in rss_env.split(",") if rss_url.strip()]
    elif kol_registry:
        rss_sources = list(kol_registry.keys())
    else:
        rss_sources = []

    if not rss_sources:
        subs = get_subscriptions()
        if subs:
            rss_sources = list(subs.keys())
            # 把訂閱清單的 label 也加進 registry（fallback）
            for url, info in subs.items():
                if url not in kol_registry:
                    kol_registry[url] = _build_kol_meta(url, info.get("label", ""), {})
        else:
            print("ℹ️  無 RSS 來源且無訂閱清單，結束。")
            print("   使用 /subpodcast <url> 訂閱後即可自動推送。")
            return

    runner = NotebookRunner()
    total_success = 0
    error_msg = ""
    send_reports = _should_send_podcast_report(mode, on_demand_chat)
    send_daily_digest = _should_send_daily_digest(mode, on_demand_chat)
    daily_digest_items: list[dict] = []
    if not send_reports:
        print("Telegram daily reports disabled; updating DB/website only.")
    if send_daily_digest:
        print(f"Daily digest enabled; collecting items from the last {DAILY_DIGEST_LOOKBACK_DAYS} day(s).")
    run_id = start_job_run("podcast_scanner", mode, len(rss_sources))
    run_error = ""

    for rss_url in rss_sources:
        kol_meta = _build_kol_meta(rss_url, "", kol_registry)
        label = kol_meta.get("label", "")
        item_id = start_job_item(run_id, rss_url, label or rss_url[:60])
        item_found = 0
        item_written = 0
        item_skipped = False
        item_error = ""

        allow_text = kol_meta.get("source_type") == "article"
        episodes = fetch_new_episodes(
            rss_url,
            mode=mode,
            chat_id=on_demand_chat,
            episode_number=episode_number,
            allow_text=allow_text,
            article_include_keywords=kol_meta.get("include_keywords"),
            article_exclude_keywords=kol_meta.get("exclude_keywords"),
        )
        item_found = len(episodes)
        if not episodes:
            print(f"🔚 [{label or rss_url[:40]}] 無新集數")
            if on_demand_chat and mode == "latest":
                error_msg = (
                    f"⚠️ 找不到第 {episode_number} 集，請確認集數是否正確。"
                    if episode_number
                    else "⚠️ 此 Podcast 目前沒有可分析的新集數。"
                )
            finish_job_item(item_id, "skipped", item_found, item_written, item_error)
            continue

        source_limit = int(kol_meta.get("max_episodes_per_run", MAX_EPISODES_PER_RUN))
        to_process = episodes[:1] if mode == "latest" else episodes[:source_limit]

        for ep in to_process:
            print(f"\n{'─' * 50}")
            print(f"📻 {ep['title']}  [{ep['published']}]")
            mp3_path = None
            try:
                kol_id = kol_meta.get("kol_id", "")
                if mode == "daily" and kol_id and episode_exists(kol_id, ep["guid"]):
                    print("  [SKIP] Episode already exists in DB; marking processed state.")
                    mark_processed(rss_url, ep["guid"], chat_id=on_demand_chat)
                    item_skipped = True
                    continue

                cached_analysis = get_cached_analysis(rss_url, ep["guid"], prompt_key)
                if cached_analysis:
                    print("  ⚡ 命中 Podcast 分析快取，跳過下載與 NotebookLM")
                    # 快取命中也要寫 DB，確保網站資訊完整
                    if _write_episode_to_db(kol_meta, ep, cached_analysis):
                        item_written += 1
                    if send_reports:
                        send_podcast_report(
                            title=ep["title"],
                            analysis=cached_analysis,
                            published=ep["published"],
                            label=label or "Podcast",
                            chat_id=on_demand_chat,
                            message_id=on_demand_msg,
                        )
                        on_demand_msg = ""
                    digest_item = _build_daily_digest_candidate(kol_meta, ep, cached_analysis)
                    if send_daily_digest and digest_item:
                        daily_digest_items.append(digest_item)
                    error_msg = ""
                    if mode == "daily":
                        mark_processed(rss_url, ep["guid"], chat_id=on_demand_chat)
                    total_success += 1
                    continue

                if ep.get("source_kind") == "article":
                    ep_prompt = _build_article_prompt(ep)
                    analysis = analyze_source_url_with_nlm(runner, ep["content_url"], ep_prompt)
                    if not analysis:
                        print("  ⚠️  NLM timeout，改用 RSS 摘要保留低信心文章訊號")
                        analysis = _fallback_article_analysis(ep)
                else:
                    ep_prompt = _build_episode_prompt(prompt, ep)
                    mp3_path = download_audio(ep["audio_url"], ep["title"])
                    if not mp3_path:
                        error_msg = f"❌ 音檔下載失敗：{ep['title'][:60]}"
                        item_error = error_msg
                        print(f"  {error_msg}")
                        continue
                    analysis = analyze_with_nlm(runner, mp3_path, ep_prompt)
                if not analysis:
                    error_msg = f"❌ AI 分析失敗（NLM 無回應），請稍後再試。\n集數：{ep['title'][:60]}"
                    print("  ❌ NLM 分析失敗")
                    continue

                if set_cached_analysis(rss_url, ep["guid"], prompt_key, analysis):
                    print(f"  💾 已寫入 Podcast 分析快取（TTL {Config.REDIS_PODCAST_TTL}s）")

                # 無論 daily 或 on-demand，分析成功就寫 DB
                if _write_episode_to_db(kol_meta, ep, analysis):
                    item_written += 1

                if send_reports:
                    send_podcast_report(
                        title=ep["title"],
                        analysis=analysis,
                        published=ep["published"],
                        label=label or "Podcast",
                        chat_id=on_demand_chat,
                        message_id=on_demand_msg,
                    )
                    on_demand_msg = ""
                digest_item = _build_daily_digest_candidate(kol_meta, ep, analysis)
                if send_daily_digest and digest_item:
                    daily_digest_items.append(digest_item)
                error_msg = ""

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

        finish_job_item(
            item_id,
            "success" if item_written > 0 else "skipped" if item_skipped else "failed",
            item_found,
            item_written,
            item_error,
        )

    print(f"\n{'=' * 55}")
    print(f"✨ 完成：成功 {total_success} 集")
    print("=" * 55)

    # Daily 模式：更新共識儀表板
    if mode == "daily" and total_success > 0:
        print("\n📊 更新 Neon DB 共識指標...")
        compute_and_write_consensus()

    if send_daily_digest:
        send_daily_investment_digest(daily_digest_items)

    finish_job_run(run_id, error_message=run_error)

    # 安全網：確保 on-demand 用戶一定收到回應
    if on_demand_chat and on_demand_msg:
        bot_token = Config.TG_BOT_TOKEN
        if bot_token:
            try:
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/deleteMessage",
                    json={"chat_id": on_demand_chat, "message_id": int(on_demand_msg)},
                    timeout=10,
                )
            except Exception:
                pass
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
