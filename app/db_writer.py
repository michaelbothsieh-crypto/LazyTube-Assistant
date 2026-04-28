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
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Optional

import psycopg2
import psycopg2.extras
import requests

DATABASE_URL: str = os.environ.get("DATABASE_URL", "")


def _get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL 未設定")
    return psycopg2.connect(DATABASE_URL)


def ensure_analytics_schema() -> bool:
    """Create the automation and signal tables used as the web SSOT."""
    if not DATABASE_URL:
        return False
    statements = [
        """
        CREATE TABLE IF NOT EXISTS kols (
          kol_id VARCHAR(100) PRIMARY KEY,
          kol_name VARCHAR(200) NOT NULL,
          host VARCHAR(200) DEFAULT '',
          avatar VARCHAR(50) DEFAULT '',
          color VARCHAR(20) DEFAULT '#6366f1',
          rss_url TEXT DEFAULT '',
          added_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS episodes (
          id SERIAL PRIMARY KEY,
          kol_id VARCHAR(100) NOT NULL REFERENCES kols(kol_id) ON DELETE CASCADE,
          guid TEXT NOT NULL,
          title TEXT NOT NULL DEFAULT '',
          published DATE,
          summary TEXT DEFAULT '',
          sentiment VARCHAR(20) DEFAULT 'neutral'
            CHECK (sentiment IN ('bullish', 'bearish', 'neutral')),
          stocks_mentioned TEXT[] DEFAULT '{}',
          report_url TEXT DEFAULT '',
          analysis_date DATE NOT NULL DEFAULT CURRENT_DATE,
          analyzed_at TIMESTAMPTZ DEFAULT NOW(),
          UNIQUE (kol_id, guid)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_episodes_date ON episodes(analysis_date DESC)",
        """
        CREATE TABLE IF NOT EXISTS consensus_daily (
          date DATE PRIMARY KEY,
          generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          episodes_analyzed INTEGER DEFAULT 0,
          consensus_score INTEGER DEFAULT 0,
          bullish_pct INTEGER DEFAULT 0,
          neutral_pct INTEGER DEFAULT 0,
          bearish_pct INTEGER DEFAULT 0,
          top_keywords TEXT[] DEFAULT '{}',
          weekly_theme TEXT DEFAULT ''
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS stock_mentions (
          date DATE NOT NULL,
          ticker VARCHAR(20) NOT NULL,
          name VARCHAR(200) DEFAULT '',
          market VARCHAR(10) DEFAULT 'US' CHECK (market IN ('TW', 'US')),
          mentions INTEGER DEFAULT 0,
          sentiment VARCHAR(20) DEFAULT 'neutral'
            CHECK (sentiment IN ('bullish', 'bearish', 'neutral')),
          kols TEXT[] DEFAULT '{}',
          PRIMARY KEY (date, ticker)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_stock_mentions_date ON stock_mentions(date DESC)",
        """
        CREATE TABLE IF NOT EXISTS job_runs (
          run_id UUID PRIMARY KEY,
          job_type VARCHAR(60) NOT NULL,
          mode VARCHAR(30) NOT NULL DEFAULT 'daily',
          status VARCHAR(20) NOT NULL DEFAULT 'running'
            CHECK (status IN ('running', 'success', 'partial', 'failed')),
          started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          finished_at TIMESTAMPTZ,
          sources_total INTEGER NOT NULL DEFAULT 0,
          sources_success INTEGER NOT NULL DEFAULT 0,
          sources_failed INTEGER NOT NULL DEFAULT 0,
          episodes_found INTEGER NOT NULL DEFAULT 0,
          episodes_written INTEGER NOT NULL DEFAULT 0,
          error_message TEXT DEFAULT ''
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_job_runs_started ON job_runs(started_at DESC)",
        """
        CREATE TABLE IF NOT EXISTS job_items (
          id BIGSERIAL PRIMARY KEY,
          run_id UUID NOT NULL REFERENCES job_runs(run_id) ON DELETE CASCADE,
          source_id TEXT NOT NULL,
          source_label TEXT DEFAULT '',
          status VARCHAR(20) NOT NULL DEFAULT 'running'
            CHECK (status IN ('running', 'success', 'skipped', 'failed')),
          episodes_found INTEGER NOT NULL DEFAULT 0,
          episodes_written INTEGER NOT NULL DEFAULT 0,
          error_message TEXT DEFAULT '',
          started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          finished_at TIMESTAMPTZ
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_job_items_run ON job_items(run_id)",
        """
        CREATE TABLE IF NOT EXISTS daily_signals (
          signal_date DATE NOT NULL,
          ticker VARCHAR(20) NOT NULL,
          name VARCHAR(200) DEFAULT '',
          market VARCHAR(10) DEFAULT 'US' CHECK (market IN ('TW', 'US')),
          direction VARCHAR(20) DEFAULT 'neutral'
            CHECK (direction IN ('bullish', 'bearish', 'neutral')),
          confidence_score INTEGER NOT NULL DEFAULT 0,
          source_count INTEGER NOT NULL DEFAULT 0,
          episode_count INTEGER NOT NULL DEFAULT 0,
          source_kols TEXT[] DEFAULT '{}',
          catalysts TEXT[] DEFAULT '{}',
          horizon VARCHAR(30) DEFAULT 'watchlist',
          thesis TEXT DEFAULT '',
          price_at_signal NUMERIC(18, 4),
          return_1d NUMERIC(8, 4),
          return_5d NUMERIC(8, 4),
          return_20d NUMERIC(8, 4),
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          PRIMARY KEY (signal_date, ticker)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_daily_signals_date ON daily_signals(signal_date DESC, confidence_score DESC)",
    ]
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                for statement in statements:
                    cur.execute(statement)
            conn.commit()
        return True
    except Exception as exc:
        print(f"  [WARN] ensure_analytics_schema failed: {exc}")
        return False


def start_job_run(job_type: str, mode: str, sources_total: int = 0) -> str:
    if not DATABASE_URL:
        return ""
    ensure_analytics_schema()
    run_id = str(uuid.uuid4())
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO job_runs (run_id, job_type, mode, sources_total) VALUES (%s, %s, %s, %s)",
                    (run_id, job_type, mode, sources_total),
                )
            conn.commit()
        return run_id
    except Exception as exc:
        print(f"  [WARN] start_job_run failed: {exc}")
        return ""


def start_job_item(run_id: str, source_id: str, source_label: str = "") -> int | None:
    if not DATABASE_URL or not run_id:
        return None
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO job_items (run_id, source_id, source_label)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (run_id, source_id, source_label),
                )
                item_id = cur.fetchone()[0]
            conn.commit()
        return int(item_id)
    except Exception as exc:
        print(f"  [WARN] start_job_item failed: {exc}")
        return None


def finish_job_item(
    item_id: int | None,
    status: str,
    episodes_found: int = 0,
    episodes_written: int = 0,
    error_message: str = "",
) -> None:
    if not DATABASE_URL or not item_id:
        return
    status = status if status in ("success", "skipped", "failed") else "failed"
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE job_items
                    SET status = %s,
                        episodes_found = %s,
                        episodes_written = %s,
                        error_message = %s,
                        finished_at = NOW()
                    WHERE id = %s
                    """,
                    (status, episodes_found, episodes_written, error_message[:800], item_id),
                )
            conn.commit()
    except Exception as exc:
        print(f"  [WARN] finish_job_item failed: {exc}")


def finish_job_run(run_id: str, status: str = "", error_message: str = "") -> None:
    if not DATABASE_URL or not run_id:
        return
    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                      COUNT(*) AS total,
                      COUNT(*) FILTER (WHERE status = 'success') AS success,
                      COUNT(*) FILTER (WHERE status = 'failed') AS failed,
                      COALESCE(SUM(episodes_found), 0) AS found,
                      COALESCE(SUM(episodes_written), 0) AS written
                    FROM job_items
                    WHERE run_id = %s
                    """,
                    (run_id,),
                )
                stats = cur.fetchone() or {}
                total = int(stats.get("total") or 0)
                success = int(stats.get("success") or 0)
                failed = int(stats.get("failed") or 0)
                final_status = status or ("success" if failed == 0 else "partial" if success > 0 else "failed")
                cur.execute(
                    """
                    UPDATE job_runs
                    SET status = %s,
                        finished_at = NOW(),
                        sources_total = %s,
                        sources_success = %s,
                        sources_failed = %s,
                        episodes_found = %s,
                        episodes_written = %s,
                        error_message = %s
                    WHERE run_id = %s
                    """,
                    (
                        final_status,
                        total,
                        success,
                        failed,
                        int(stats.get("found") or 0),
                        int(stats.get("written") or 0),
                        error_message[:1000],
                        run_id,
                    ),
                )
            conn.commit()
    except Exception as exc:
        print(f"  [WARN] finish_job_run failed: {exc}")


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


def _price_symbol(ticker: str, market: str) -> str:
    return f"{ticker}.tw" if market == "TW" else f"{ticker.lower()}.us"


def _fetch_price_at_signal(ticker: str, market: str) -> float | None:
    """Best-effort market snapshot from Stooq. Signal remains valid if this fails."""
    try:
        resp = requests.get(
            "https://stooq.com/q/l/",
            params={"s": _price_symbol(ticker, market), "f": "sd2t2ohlcv", "h": "", "e": "csv"},
            timeout=8,
        )
        resp.raise_for_status()
        lines = [line.strip() for line in resp.text.splitlines() if line.strip()]
        if len(lines) < 2:
            return None
        fields = lines[1].split(",")
        close = fields[6] if len(fields) > 6 else ""
        if close and close.upper() != "N/D":
            return float(close)
    except Exception:
        return None
    return None


def _extract_catalysts(summaries: list[str], tickers: list[str]) -> list[str]:
    keyword_map = {
        "AI": ["AI", "人工智慧", "算力"],
        "半導體": ["半導體", "晶片", "CoWoS", "先進製程"],
        "財報": ["財報", "EPS", "營收", "毛利"],
        "利率": ["Fed", "利率", "降息", "升息"],
        "雲端": ["cloud", "雲端", "資料中心"],
        "估值": ["估值", "本益比", "PER", "EV/EBITDA"],
    }
    text = "\n".join(summaries).lower()
    catalysts = [label for label, words in keyword_map.items() if any(word.lower() in text for word in words)]
    for ticker in tickers[:3]:
        if ticker not in catalysts:
            catalysts.append(ticker)
    return catalysts[:6]


def _infer_horizon(summaries: list[str]) -> str:
    text = "\n".join(summaries).lower()
    if any(word in text for word in ["長線", "long-term", "長期"]):
        return "long-term"
    if any(word in text for word in ["短線", "swing", "波段"]):
        return "swing"
    if any(word in text for word in ["財報", "earnings", "事件"]):
        return "event-driven"
    return "watchlist"


def _write_daily_signals(cur, signal_date: date, rows: list[dict]) -> None:
    cur.execute("DELETE FROM daily_signals WHERE signal_date = %s", (signal_date,))
    for row in rows:
        name, market = _stock_info(row["ticker"])
        source_count = len(set(row["kols"]))
        episode_count = row["mentions"]
        confidence = min(100, round(source_count * 18 + episode_count * 8))
        summaries = row.get("summaries", [])
        catalysts = _extract_catalysts(summaries, [row["ticker"]])
        horizon = _infer_horizon(summaries)
        thesis = (
            f"{row['ticker']} appeared across {source_count} source(s) and "
            f"{episode_count} episode(s). Dominant direction: {row['sentiment']}."
        )
        price = _fetch_price_at_signal(row["ticker"], market)
        cur.execute(
            """
            INSERT INTO daily_signals
              (signal_date, ticker, name, market, direction, confidence_score,
               source_count, episode_count, source_kols, catalysts, horizon,
               thesis, price_at_signal, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (signal_date, ticker) DO UPDATE SET
              name = EXCLUDED.name,
              market = EXCLUDED.market,
              direction = EXCLUDED.direction,
              confidence_score = EXCLUDED.confidence_score,
              source_count = EXCLUDED.source_count,
              episode_count = EXCLUDED.episode_count,
              source_kols = EXCLUDED.source_kols,
              catalysts = EXCLUDED.catalysts,
              horizon = EXCLUDED.horizon,
              thesis = EXCLUDED.thesis,
              price_at_signal = COALESCE(EXCLUDED.price_at_signal, daily_signals.price_at_signal),
              updated_at = NOW()
            """,
            (
                signal_date,
                row["ticker"],
                name,
                market,
                row["sentiment"],
                confidence,
                source_count,
                episode_count,
                row["kols"],
                catalysts,
                horizon,
                thesis,
                price,
            ),
        )


def compute_and_write_consensus(analysis_date: Optional[date] = None) -> bool:
    """
    從 episodes 表讀取今日資料，計算共識指標並寫入：
      - consensus_daily
      - stock_mentions
    """
    if not DATABASE_URL:
        return False

    today = analysis_date or date.today()
    ensure_analytics_schema()

    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT e.kol_id, k.kol_name, e.sentiment, e.stocks_mentioned, e.summary
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
        stock_summaries: dict[str, list[str]] = defaultdict(list)
        for r in rows:
            for ticker in (r["stocks_mentioned"] or []):
                stock_kols[ticker].append(r["kol_name"])
                stock_sent[ticker].append(r["sentiment"])
                if r.get("summary"):
                    stock_summaries[ticker].append(r["summary"])

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
                "summaries": stock_summaries[ticker],
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

                _write_daily_signals(cur, today, stock_rows)
            conn.commit()

        print(f"  [OK] Consensus updated: score={consensus_score} bullish={bullish_pct}%"
              f" ({n} eps, {len(stock_rows)} stocks)")
        return True

    except Exception as exc:
        print(f"  [WARN] compute_and_write_consensus failed: {exc}")
        return False
