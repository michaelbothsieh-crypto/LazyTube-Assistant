-- LazyTube / PodConsensus — Neon PostgreSQL Schema
-- Run once to initialize; safe to re-run (idempotent).

-- ─────────────────────────────────────────────────────
-- KOL channel registry
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kols (
  kol_id    VARCHAR(100) PRIMARY KEY,
  kol_name  VARCHAR(200) NOT NULL,
  host      VARCHAR(200) DEFAULT '',
  avatar    VARCHAR(50)  DEFAULT '🎙️',
  color     VARCHAR(20)  DEFAULT '#6366f1',
  rss_url   TEXT         DEFAULT '',
  added_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────
-- Episode analysis results (one row per analyzed episode)
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS episodes (
  id               SERIAL PRIMARY KEY,
  kol_id           VARCHAR(100) NOT NULL REFERENCES kols(kol_id) ON DELETE CASCADE,
  guid             TEXT         NOT NULL,
  title            TEXT         NOT NULL DEFAULT '',
  published        DATE,
  summary          TEXT         DEFAULT '',
  sentiment        VARCHAR(20)  DEFAULT 'neutral'
                   CHECK (sentiment IN ('bullish', 'bearish', 'neutral')),
  stocks_mentioned TEXT[]       DEFAULT '{}',
  report_url       TEXT         DEFAULT '',
  analysis_date    DATE         NOT NULL DEFAULT CURRENT_DATE,
  analyzed_at      TIMESTAMPTZ  DEFAULT NOW(),
  UNIQUE (kol_id, guid)
);

CREATE INDEX IF NOT EXISTS idx_episodes_date ON episodes(analysis_date DESC);

-- ─────────────────────────────────────────────────────
-- Daily consensus metrics (computed from episodes after each scan)
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS consensus_daily (
  date              DATE PRIMARY KEY,
  generated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  episodes_analyzed INTEGER      DEFAULT 0,
  consensus_score   INTEGER      DEFAULT 0,
  bullish_pct       INTEGER      DEFAULT 0,
  neutral_pct       INTEGER      DEFAULT 0,
  bearish_pct       INTEGER      DEFAULT 0,
  top_keywords      TEXT[]       DEFAULT '{}',
  weekly_theme      TEXT         DEFAULT ''
);

-- ─────────────────────────────────────────────────────
-- Stock mention aggregation per day
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stock_mentions (
  date      DATE         NOT NULL,
  ticker    VARCHAR(20)  NOT NULL,
  name      VARCHAR(200) DEFAULT '',
  market    VARCHAR(10)  DEFAULT 'US'
            CHECK (market IN ('TW', 'US')),
  mentions  INTEGER      DEFAULT 0,
  sentiment VARCHAR(20)  DEFAULT 'neutral'
            CHECK (sentiment IN ('bullish', 'bearish', 'neutral')),
  kols      TEXT[]       DEFAULT '{}',
  PRIMARY KEY (date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_stock_mentions_date ON stock_mentions(date DESC);

-- Automation run ledger. One row per scheduled/manual scanner run.
CREATE TABLE IF NOT EXISTS job_runs (
  run_id          UUID PRIMARY KEY,
  job_type        VARCHAR(60) NOT NULL,
  mode            VARCHAR(30) NOT NULL DEFAULT 'daily',
  status          VARCHAR(20) NOT NULL DEFAULT 'running'
                  CHECK (status IN ('running', 'success', 'partial', 'failed')),
  started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at     TIMESTAMPTZ,
  sources_total   INTEGER NOT NULL DEFAULT 0,
  sources_success INTEGER NOT NULL DEFAULT 0,
  sources_failed  INTEGER NOT NULL DEFAULT 0,
  episodes_found  INTEGER NOT NULL DEFAULT 0,
  episodes_written INTEGER NOT NULL DEFAULT 0,
  error_message   TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_job_runs_started ON job_runs(started_at DESC);

-- Per-source observability for a job run.
CREATE TABLE IF NOT EXISTS job_items (
  id              BIGSERIAL PRIMARY KEY,
  run_id          UUID NOT NULL REFERENCES job_runs(run_id) ON DELETE CASCADE,
  source_id       TEXT NOT NULL,
  source_label    TEXT DEFAULT '',
  status          VARCHAR(20) NOT NULL DEFAULT 'running'
                  CHECK (status IN ('running', 'success', 'skipped', 'failed')),
  episodes_found  INTEGER NOT NULL DEFAULT 0,
  episodes_written INTEGER NOT NULL DEFAULT 0,
  error_message   TEXT DEFAULT '',
  started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_job_items_run ON job_items(run_id);

-- Finance signal SSOT. Derived from episodes, consumed by the web UI.
CREATE TABLE IF NOT EXISTS daily_signals (
  signal_date      DATE NOT NULL,
  ticker           VARCHAR(20) NOT NULL,
  name             VARCHAR(200) DEFAULT '',
  market           VARCHAR(10) DEFAULT 'US' CHECK (market IN ('TW', 'US')),
  direction        VARCHAR(20) DEFAULT 'neutral'
                   CHECK (direction IN ('bullish', 'bearish', 'neutral')),
  confidence_score INTEGER NOT NULL DEFAULT 0,
  source_count     INTEGER NOT NULL DEFAULT 0,
  episode_count    INTEGER NOT NULL DEFAULT 0,
  source_kols      TEXT[] DEFAULT '{}',
  catalysts        TEXT[] DEFAULT '{}',
  horizon          VARCHAR(30) DEFAULT 'watchlist',
  thesis           TEXT DEFAULT '',
  price_at_signal  NUMERIC(18, 4),
  return_1d        NUMERIC(8, 4),
  return_5d        NUMERIC(8, 4),
  return_20d       NUMERIC(8, 4),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (signal_date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_daily_signals_date ON daily_signals(signal_date DESC, confidence_score DESC);

-- ─────────────────────────────────────────────────────
-- Seed: KOL registry from latest.json
-- ─────────────────────────────────────────────────────
INSERT INTO kols (kol_id, kol_name, host, avatar, color) VALUES
  ('gooaye',      '股癌',                    '謝孟恭',    '🦀', '#3b82f6'),
  ('yutin',       '游庭皓的財經皓角',          '游庭皓',    '📊', '#10b981'),
  ('macromicro',  'MacroMicro 財經M平方',     'Rachel',   '🌐', '#8b5cf6'),
  ('billkitchen', '比爾的財經廚房',            '楊比爾',    '🍳', '#f59e0b'),
  ('zhaohualink', '兆華與股惑仔',             '李兆華',    '📈', '#ef4444'),
  ('caalaw',      '財報狗',                   'Jeff & Sky','🐕', '#14b8a6'),
  ('shenghong',   '升鴻投資',                 '升鴻',      '🚀', '#06b6d4'),
  ('investlab',   '阿福の台美股研究室',         '阿福',      '🔬', '#6366f1')
ON CONFLICT (kol_id) DO NOTHING;

-- ─────────────────────────────────────────────────────
-- Seed: Episodes from latest.json (2026-04-23 ~ 2026-04-26)
-- ─────────────────────────────────────────────────────
INSERT INTO episodes (kol_id, guid, title, published, summary, sentiment, stocks_mentioned, report_url, analysis_date) VALUES
  ('gooaye',      'gooaye-20260426', 'EP655 - 法說季前的布局思路',
   '2026-04-26', '謝孟恭認為 AI 伺服器需求未見頂，NVDA 雖然短線超漲但長線邏輯不變；台積電法說前市場情緒偏正面，建議持有。',
   'bullish', ARRAY['NVDA','2330','META'], '', '2026-04-26'),
  ('yutin',       'yutin-20260426', '4/26 早報 - 外資連三買，台股站穩 2 萬 2',
   '2026-04-26', '外資連續三天買超，台積電帶動權值股走強，盤勢仍偏多；美債殖利率小幅回落，有利科技股估值。',
   'bullish', ARRAY['2330','MSFT'], '', '2026-04-26'),
  ('macromicro',  'macromicro-20260425', '降息路徑分析：2026 下半年的機會',
   '2026-04-25', '從 PMI 與就業數據來看，美國軟著陸機率提升；M平方預期 Fed 第三季開始降息，有利風險資產。',
   'bullish', ARRAY['2330'], '', '2026-04-25'),
  ('billkitchen', 'billkitchen-20260425', '聊聊大類資產配置：債券 vs 股票',
   '2026-04-25', '在降息預期下，比爾建議增加科技股比重，適度減少短債；META 廣告業務超預期，AI 整合效果顯現。',
   'bullish', ARRAY['META','MSFT','AMZN'], '', '2026-04-25'),
  ('zhaohualink', 'zhaohualink-20260424', 'EP184 - 台股再創歷史新高的思考',
   '2026-04-24', '台股指數創新高但中小型股落差大，兆華提醒注意籌碼面分歧；聯發科基本面改善，值得關注。',
   'neutral', ARRAY['2454','3008'], '', '2026-04-24'),
  ('caalaw',      'caalaw-20260424', '台積電 & 聯發科財報前瞻',
   '2026-04-24', '法說季前，財報狗分析台積電 CoWoS 產能持續滿載，聯發科手機晶片庫存回歸健康。',
   'bullish', ARRAY['2330','2454','NVDA'], '', '2026-04-24'),
  ('shenghong',   'shenghong-20260424', 'NVDA 技術面解析',
   '2026-04-24', 'NVDA 突破前高，市場動能強勁；升鴻認為短線可能震盪但趨勢向上，META 廣告收益持續成長。',
   'bullish', ARRAY['NVDA','META','AMZN'], '', '2026-04-24'),
  ('investlab',   'investlab-20260423', '台積電佈局時機討論',
   '2026-04-23', '阿福從 PER 與 EV/EBITDA 角度分析台積電仍有上漲空間；聯發科 AI 手機晶片為下一個成長引擎。',
   'bullish', ARRAY['2330','2454'], '', '2026-04-23')
ON CONFLICT (kol_id, guid) DO NOTHING;

-- ─────────────────────────────────────────────────────
-- Seed: Consensus history
-- ─────────────────────────────────────────────────────
INSERT INTO consensus_daily (date, generated_at, episodes_analyzed, consensus_score, bullish_pct, neutral_pct, bearish_pct, top_keywords, weekly_theme) VALUES
  ('2026-04-26', '2026-04-26T09:47:00+08:00', 8, 81, 67, 19, 14,
   ARRAY['AI伺服器','法說季','台積電','降息預期','供應鏈'],
   'AI 資本支出浪潮持續，法說季前市場偏多，台積電再創新高'),
  ('2026-04-25', '2026-04-25T09:47:00+08:00', 5, 74, 61, 28, 11,
   ARRAY['台積電','降息預期','AI伺服器','META','債券'],
   '外資持續回補，AI 題材帶動台美股同步偏多'),
  ('2026-04-24', '2026-04-24T09:47:00+08:00', 6, 78, 64, 22, 14,
   ARRAY['台積電','NVDA','法說季','AI伺服器','聯發科'],
   '法說季登場，台積電與 NVDA 共識強度升至年內高點'),
  ('2026-04-23', '2026-04-23T09:47:00+08:00', 4, 69, 58, 30, 12,
   ARRAY['台積電','聯發科','降息預期','NVDA','供應鏈'],
   '法說季前夕，多方氣氛濃但籌碼面仍需觀察'),
  ('2026-04-22', '2026-04-22T09:47:00+08:00', 3, 55, 45, 38, 17,
   ARRAY['台積電','降息','觀望','外資','殖利率'],
   '市場觀望法說季，共識分數回落至中性區間'),
  ('2026-04-21', '2026-04-21T09:47:00+08:00', 4, 62, 52, 33, 15,
   ARRAY['NVDA','AI伺服器','台積電','法說季','降息'],
   'NVDA 帶動科技類股回溫，市場情緒由中性轉偏多'),
  ('2026-04-18', '2026-04-18T09:47:00+08:00', 5, 70, 60, 29, 11,
   ARRAY['台積電','AI伺服器','NVDA','降息預期','法說季'],
   '週末前多方信心增強，AI 算力需求維持正向預期')
ON CONFLICT (date) DO NOTHING;

-- ─────────────────────────────────────────────────────
-- Seed: Stock mentions for 2026-04-26
-- ─────────────────────────────────────────────────────
INSERT INTO stock_mentions (date, ticker, name, market, mentions, sentiment, kols) VALUES
  ('2026-04-26', 'NVDA',  '輝達',   'US', 8, 'bullish', ARRAY['股癌','游庭皓','財報狗','升鴻投資','比爾']),
  ('2026-04-26', '2330',  '台積電', 'TW', 7, 'bullish', ARRAY['股癌','財報狗','M平方','兆華','阿福']),
  ('2026-04-26', 'META',  'Meta',   'US', 5, 'bullish', ARRAY['股癌','比爾','升鴻投資']),
  ('2026-04-26', '2454',  '聯發科', 'TW', 4, 'neutral', ARRAY['兆華','財報狗','阿福']),
  ('2026-04-26', 'MSFT',  '微軟',   'US', 4, 'bullish', ARRAY['游庭皓','比爾']),
  ('2026-04-26', 'AMZN',  '亞馬遜', 'US', 3, 'bullish', ARRAY['比爾','升鴻投資']),
  ('2026-04-26', '3008',  '大立光', 'TW', 3, 'neutral', ARRAY['兆華','小朋友']),
  ('2026-04-26', 'GOOGL', 'Google', 'US', 3, 'bullish', ARRAY['股癌','游庭皓'])
ON CONFLICT (date, ticker) DO NOTHING;
