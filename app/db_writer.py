"""
db_writer.py — Neon PostgreSQL 寫入模組

從 podcast_scanner.py 呼叫，負責：
  1. 把每集分析結果寫入 episodes 表
  2. 寫完所有集數後，計算並更新 consensus_daily + stock_mentions
"""
from __future__ import annotations

import os
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Optional

import psycopg2
import psycopg2.extras

DATABASE_URL: str = os.environ.get("DATABASE_URL", "")


def _get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL 未設定")
    return psycopg2.connect(DATABASE_URL)


# ── KOL / slug helpers ──────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """RSS feed title → safe kol_id slug (≤24 chars)."""
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:24].rstrip("-") or "kol"


def ensure_kol(kol_meta: dict) -> str:
    """
    Upsert KOL from a metadata dict (from website_kols.json or fallback).
    Required key: kol_id. Optional: label/kol_name, host, avatar, color, rss_url.
    Returns kol_id.
    """
    kol_id = kol_meta["kol_id"]
    kol_name = kol_meta.get("label") or kol_meta.get("kol_name") or kol_id
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO kols (kol_id, kol_name, host, avatar, color, rss_url)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (kol_id) DO UPDATE SET
                  kol_name = EXCLUDED.kol_name,
                  host     = COALESCE(NULLIF(EXCLUDED.host,   ''), kols.host),
                  avatar   = COALESCE(NULLIF(EXCLUDED.avatar, ''), kols.avatar),
                  color    = COALESCE(NULLIF(EXCLUDED.color,  ''), kols.color),
                  rss_url  = COALESCE(NULLIF(EXCLUDED.rss_url,''), kols.rss_url)
                """,
                (
                    kol_id,
                    kol_name,
                    kol_meta.get("host", ""),
                    kol_meta.get("avatar", "🎙️"),
                    kol_meta.get("color", "#6366f1"),
                    kol_meta.get("rss_url", ""),
                ),
            )
        conn.commit()
    return kol_id


# ── Episode write ────────────────────────────────────────────────────────────

def write_episode(
    kol_id: str,
    guid: str,
    title: str,
    published_str: str,
    summary: str,
    sentiment: str,
    stocks_mentioned: list[str],
    report_url: str = "",
    analysis_date: Optional[date] = None,
) -> bool:
    """
    寫入（或更新）一集分析結果。
    回傳 True 代表成功，False 代表失敗。
    """
    if not DATABASE_URL:
        return False

    try:
        # 解析發布日期
        pub_date: Optional[date] = None
        if published_str:
            try:
                pub_date = datetime.strptime(published_str[:10], "%Y-%m-%d").date()
            except ValueError:
                pass

        today = analysis_date or date.today()
        sentiment = sentiment if sentiment in ("bullish", "bearish", "neutral") else "neutral"

        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO episodes
                      (kol_id, guid, title, published, summary, sentiment,
                       stocks_mentioned, report_url, analysis_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (kol_id, guid) DO UPDATE SET
                      summary          = EXCLUDED.summary,
                      sentiment        = EXCLUDED.sentiment,
                      stocks_mentioned = EXCLUDED.stocks_mentioned,
                      report_url       = EXCLUDED.report_url,
                      analyzed_at      = NOW()
                    """,
                    (
                        kol_id, guid, title, pub_date, summary,
                        sentiment, stocks_mentioned, report_url, today,
                    ),
                )
            conn.commit()
        return True
    except Exception as exc:
        print(f"  ⚠️  DB write_episode 失敗：{exc}")
        return False


# ── Consensus computation ────────────────────────────────────────────────────

# 已知股票名稱對應表（擴充請直接在此 dict 新增）
_STOCK_NAMES: dict[str, tuple[str, str]] = {
    "NVDA": ("輝達", "US"),    "TSLA": ("特斯拉", "US"),
    "META": ("Meta", "US"),    "GOOGL": ("Google", "US"),
    "MSFT": ("微軟", "US"),    "AMZN": ("亞馬遜", "US"),
    "AAPL": ("蘋果", "US"),    "AMD": ("超微", "US"),
    "2330": ("台積電", "TW"),  "2454": ("聯發科", "TW"),
    "3008": ("大立光", "TW"),  "2308": ("台達電", "TW"),
    "2317": ("鴻海", "TW"),    "2382": ("廣達", "TW"),
    "2881": ("富邦金", "TW"),  "2882": ("國泰金", "TW"),
}

def _stock_info(ticker: str) -> tuple[str, str]:
    """回傳 (name, market)，未知 ticker 依開頭數字判斷市場。"""
    if ticker in _STOCK_NAMES:
        return _STOCK_NAMES[ticker]
    market = "TW" if ticker[:1].isdigit() else "US"
    return (ticker, market)


def compute_and_write_consensus(analysis_date: Optional[date] = None) -> bool:
    """
    從 episodes 表讀取今日資料，計算共識指標並寫入：
      - consensus_daily
      - stock_mentions
    """
    if not DATABASE_URL:
        return False

    today = analysis_date or date.today()

    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT e.kol_id, k.kol_name, e.sentiment, e.stocks_mentioned
                    FROM episodes e
                    JOIN kols k ON k.kol_id = e.kol_id
                    WHERE e.analysis_date = %s
                    """,
                    (today,),
                )
                rows = cur.fetchall()

        if not rows:
            print(f"  [INFO] {today} no episodes, skipping consensus")
            return True

        # ── Sentiment distribution ────────────────────────────────────────
        n = len(rows)
        sent_counter: Counter[str] = Counter(r["sentiment"] for r in rows)
        bullish_pct = round(sent_counter["bullish"] / n * 100)
        bearish_pct = round(sent_counter["bearish"] / n * 100)
        neutral_pct = 100 - bullish_pct - bearish_pct

        # ── Stock aggregation ─────────────────────────────────────────────
        stock_kols: dict[str, list[str]] = defaultdict(list)
        stock_sent: dict[str, list[str]] = defaultdict(list)
        for r in rows:
            for ticker in (r["stocks_mentioned"] or []):
                stock_kols[ticker].append(r["kol_name"])
                stock_sent[ticker].append(r["sentiment"])

        # Dominant sentiment per stock
        def dominant(sents: list[str]) -> str:
            c = Counter(sents)
            return c.most_common(1)[0][0]

        stock_rows = [
            {
                "ticker": ticker,
                "mentions": len(kols),
                "sentiment": dominant(stock_sent[ticker]),
                "kols": kols,
            }
            for ticker, kols in sorted(stock_kols.items(), key=lambda x: -len(x[1]))
        ]

        # ── Consensus score ───────────────────────────────────────────────
        # Weighted: bullish % × (unique stock consensus depth / 10) capped at 100
        unique_bullish_stocks = sum(
            1 for s in stock_rows if s["sentiment"] == "bullish"
        )
        depth_bonus = min(unique_bullish_stocks, 10)
        consensus_score = min(100, round(bullish_pct * 0.8 + depth_bonus * 2))

        # ── Keywords: top 5 tickers by mentions ──────────────────────────
        top_keywords = [r["ticker"] for r in stock_rows[:5]]

        # ── Weekly theme ──────────────────────────────────────────────────
        top3 = " / ".join(r["ticker"] for r in stock_rows[:3])
        if bullish_pct >= 60:
            mood = "偏多"
        elif bearish_pct >= 30:
            mood = "謹慎"
        else:
            mood = "中性"
        weekly_theme = f"今日 {n} 集分析，{top3} 為高共識標的，市場情緒{mood}"

        # ── Write to DB ───────────────────────────────────────────────────
        with _get_conn() as conn:
            with conn.cursor() as cur:
                # consensus_daily
                cur.execute(
                    """
                    INSERT INTO consensus_daily
                      (date, generated_at, episodes_analyzed, consensus_score,
                       bullish_pct, neutral_pct, bearish_pct, top_keywords, weekly_theme)
                    VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date) DO UPDATE SET
                      generated_at      = NOW(),
                      episodes_analyzed = EXCLUDED.episodes_analyzed,
                      consensus_score   = EXCLUDED.consensus_score,
                      bullish_pct       = EXCLUDED.bullish_pct,
                      neutral_pct       = EXCLUDED.neutral_pct,
                      bearish_pct       = EXCLUDED.bearish_pct,
                      top_keywords      = EXCLUDED.top_keywords,
                      weekly_theme      = EXCLUDED.weekly_theme
                    """,
                    (today, n, consensus_score,
                     bullish_pct, neutral_pct, bearish_pct,
                     top_keywords, weekly_theme),
                )

                # stock_mentions — delete today's rows first, then re-insert
                cur.execute("DELETE FROM stock_mentions WHERE date = %s", (today,))
                for s in stock_rows:
                    name, market = _stock_info(s["ticker"])
                    cur.execute(
                        """
                        INSERT INTO stock_mentions
                          (date, ticker, name, market, mentions, sentiment, kols)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (today, s["ticker"], name, market,
                         s["mentions"], s["sentiment"], s["kols"]),
                    )
            conn.commit()

        print(f"  [OK] Consensus updated: score={consensus_score} bullish={bullish_pct}%"
              f" ({n} eps, {len(stock_rows)} stocks)")
        return True

    except Exception as exc:
        print(f"  [WARN] compute_and_write_consensus failed: {exc}")
        return False
