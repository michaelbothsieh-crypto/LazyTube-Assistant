import { neon } from '@neondatabase/serverless'
import { unstable_cache } from 'next/cache'
import type { ConsensusData, ConsensusHistory, DailySignal, Episode, JobRun, Stock } from '@/types'

function sql() {
  const url = process.env.DATABASE_URL
  if (!url) return null
  return neon(url)
}

export const getLatestData = unstable_cache(
  _getLatestData,
  ['latest-consensus-data'],
  { revalidate: 300, tags: ['consensus'] },
)

async function _getLatestData(): Promise<ConsensusData> {
  const db = sql()
  if (!db) return emptyConsensusData()

  try {
    const [consensus] = await db`
      SELECT *
      FROM consensus_daily
      WHERE date >= CURRENT_DATE - INTERVAL '2 days'
      ORDER BY date DESC
      LIMIT 1
    `

    if (!consensus) return emptyConsensusData()

    const latestDateValue = consensus.date instanceof Date ? consensus.date : new Date(String(consensus.date))
    const latestDate: string = consensus.date instanceof Date
      ? consensus.date.toISOString().slice(0, 10)
      : String(consensus.date)

    const [stocks, episodes, history, signals, runs] = await Promise.all([
      db`
        SELECT ticker, name, market, mentions, sentiment, kols
        FROM stock_mentions
        WHERE date = (
          SELECT MAX(date)
          FROM stock_mentions
          WHERE date <= ${latestDateValue}
        )
        ORDER BY mentions DESC
      `,
      db`
        WITH recent_episodes AS (
          SELECT e.kol_id AS episode_kol_id,
                 COALESCE(NULLIF(k.rss_url, ''), e.kol_id) AS source_key,
                 e.title, e.published, e.summary, e.sentiment,
                 e.stocks_mentioned, e.report_url, e.analyzed_at
          FROM episodes e
          JOIN kols k ON k.kol_id = e.kol_id
          WHERE e.published >= CURRENT_DATE - INTERVAL '2 days'
        ),
        latest_episodes AS (
          SELECT DISTINCT ON (source_key) *
          FROM recent_episodes
          ORDER BY source_key, published DESC NULLS LAST, analyzed_at DESC
        ),
        canonical_kols AS (
          SELECT DISTINCT ON (COALESCE(NULLIF(rss_url, ''), kol_id))
                 COALESCE(NULLIF(rss_url, ''), kol_id) AS source_key,
                 kol_id, kol_name, host, avatar, color
          FROM kols
          WHERE POSITION('://' IN kol_name) = 0
          ORDER BY COALESCE(NULLIF(rss_url, ''), kol_id), added_at ASC
        )
        SELECT k.kol_id, k.kol_name, k.host, k.avatar, k.color,
               e.title, e.published, e.summary, e.sentiment,
               e.stocks_mentioned, e.report_url, e.analyzed_at
        FROM latest_episodes e
        JOIN canonical_kols k ON k.source_key = e.source_key
        ORDER BY published DESC NULLS LAST, analyzed_at DESC
      `,
      db`
        SELECT date, consensus_score, top_keywords[1] AS top_stock, bullish_pct
        FROM consensus_daily
        ORDER BY date DESC
        LIMIT 30
      `,
      db`
        SELECT signal_date, ticker, name, market, direction, confidence_score,
               source_count, episode_count, source_kols, catalysts, horizon,
               thesis, price_at_signal, return_1d, return_5d, return_20d
        FROM daily_signals
        WHERE signal_date = (
          SELECT MAX(signal_date)
          FROM daily_signals
          WHERE signal_date <= ${latestDateValue}
        )
        ORDER BY confidence_score DESC, source_count DESC
        LIMIT 12
      `,
      db`
        SELECT run_id, job_type, mode, status, started_at, finished_at,
               sources_total, sources_success, sources_failed,
               episodes_found, episodes_written
        FROM job_runs
        WHERE job_type = 'podcast_scanner'
        ORDER BY started_at DESC
        LIMIT 1
      `,
    ])

    return {
      generated_at: consensus.generated_at instanceof Date
        ? consensus.generated_at.toISOString()
        : String(consensus.generated_at),
      date: latestDate,
      episodes_analyzed: Number(consensus.episodes_analyzed),
      consensus: {
        stocks: stocks.map((stock): Stock => ({
          ticker: stock.ticker,
          name: stock.name,
          market: stock.market as 'TW' | 'US',
          mentions: Number(stock.mentions),
          sentiment: stock.sentiment as 'bullish' | 'bearish' | 'neutral',
          kols: stock.kols ?? [],
        })),
        market_sentiment: {
          bullish: Number(consensus.bullish_pct),
          neutral: Number(consensus.neutral_pct),
          bearish: Number(consensus.bearish_pct),
        },
        consensus_score: Number(consensus.consensus_score),
        top_keywords: consensus.top_keywords ?? [],
        weekly_theme: consensus.weekly_theme ?? '',
      },
      episodes: episodes.map(mapEpisodeRow),
      consensus_history: [...history].reverse().map(mapHistoryRow),
      signals: signals.map(mapSignalRow),
      automation: automationFromRun(runs[0]),
    }
  } catch {
    return emptyConsensusData()
  }
}

export async function getEpisodeByKolId(kolId: string): Promise<Episode | null> {
  const db = sql()
  if (!db) return null

  try {
    const rows = await db`
      WITH target AS (
        SELECT COALESCE(NULLIF(rss_url, ''), kol_id) AS source_key
        FROM kols
        WHERE kol_id = ${kolId}
        LIMIT 1
      ),
      canonical_kol AS (
        SELECT DISTINCT ON (COALESCE(NULLIF(k.rss_url, ''), k.kol_id))
               COALESCE(NULLIF(k.rss_url, ''), k.kol_id) AS source_key,
               k.kol_id, k.kol_name, k.host, k.avatar, k.color
        FROM kols k
        JOIN target t ON t.source_key = COALESCE(NULLIF(k.rss_url, ''), k.kol_id)
        WHERE POSITION('://' IN k.kol_name) = 0
        ORDER BY COALESCE(NULLIF(k.rss_url, ''), k.kol_id), k.added_at ASC
      ),
      latest_episode AS (
        SELECT e.title, e.published, e.summary, e.sentiment,
               e.stocks_mentioned, e.report_url, e.analyzed_at
        FROM episodes e
        JOIN kols k ON k.kol_id = e.kol_id
        JOIN target t ON t.source_key = COALESCE(NULLIF(k.rss_url, ''), k.kol_id)
        ORDER BY e.published DESC NULLS LAST, e.analyzed_at DESC
        LIMIT 1
      )
      SELECT k.kol_id, k.kol_name, k.host, k.avatar, k.color,
             e.title, e.published, e.summary, e.sentiment,
             e.stocks_mentioned, e.report_url
      FROM latest_episode e
      CROSS JOIN canonical_kol k
      LIMIT 1
    `
    return rows.length ? mapEpisodeRow(rows[0]) : null
  } catch {
    return null
  }
}

export async function getAllKolIds(): Promise<string[]> {
  const db = sql()
  if (!db) return []

  try {
    const rows = await db`
      WITH canonical_kols AS (
        SELECT DISTINCT ON (COALESCE(NULLIF(rss_url, ''), kol_id))
               COALESCE(NULLIF(rss_url, ''), kol_id) AS source_key,
               kol_id
        FROM kols
        WHERE POSITION('://' IN kol_name) = 0
        ORDER BY COALESCE(NULLIF(rss_url, ''), kol_id), added_at ASC
      )
      SELECT ck.kol_id
      FROM canonical_kols ck
      WHERE EXISTS (
        SELECT 1
        FROM episodes e
        JOIN kols k ON k.kol_id = e.kol_id
        WHERE COALESCE(NULLIF(k.rss_url, ''), k.kol_id) = ck.source_key
          AND COALESCE(cardinality(e.stocks_mentioned), 0) > 0
      )
      ORDER BY ck.kol_id
    `
    return rows.map((row) => row.kol_id as string)
  } catch {
    return []
  }
}

export const getLatestStocks = unstable_cache(
  async (): Promise<Stock[]> => {
    const db = sql()
    if (!db) return []

    try {
      const rows = await db`
        SELECT sm.ticker, sm.name, sm.market, sm.mentions, sm.sentiment, sm.kols
        FROM stock_mentions sm
        WHERE sm.date = (
          SELECT MAX(date)
          FROM consensus_daily
          WHERE date >= CURRENT_DATE - INTERVAL '2 days'
        )
        ORDER BY sm.mentions DESC
      `
      return rows.map((stock): Stock => ({
        ticker: stock.ticker,
        name: stock.name,
        market: stock.market as 'TW' | 'US',
        mentions: Number(stock.mentions),
        sentiment: stock.sentiment as 'bullish' | 'bearish' | 'neutral',
        kols: stock.kols ?? [],
      }))
    } catch {
      return []
    }
  },
  ['latest-stocks'],
  { revalidate: 300 },
)

export const getConsensusHistory = unstable_cache(
  async (): Promise<ConsensusHistory[]> => {
    const db = sql()
    if (!db) return []

    try {
      const rows = await db`
        SELECT date, consensus_score, top_keywords[1] AS top_stock, bullish_pct
        FROM consensus_daily
        ORDER BY date ASC
        LIMIT 30
      `
      return rows.map(mapHistoryRow)
    } catch {
      return []
    }
  },
  ['consensus-history'],
  { revalidate: 300 },
)

function mapEpisodeRow(row: Record<string, unknown>): Episode {
  const summary = stripNotebookCitations(String(row.summary ?? ''))
  const stocks = Array.isArray(row.stocks_mentioned) ? row.stocks_mentioned as string[] : []
  const sentiment = row.sentiment as 'bullish' | 'bearish' | 'neutral'

  return {
    kol_id: String(row.kol_id ?? ''),
    kol_name: String(row.kol_name ?? ''),
    host: String(row.host ?? ''),
    avatar: String(row.avatar ?? ''),
    color: String(row.color ?? '#73f1ba'),
    title: stripNotebookCitations(String(row.title ?? '')),
    published: row.published instanceof Date
      ? row.published.toISOString().slice(0, 10)
      : String(row.published ?? ''),
    summary,
    sentiment,
    stocks_mentioned: stocks,
    report_url: String(row.report_url ?? ''),
    unique_insight: deriveUniqueInsight(summary, stocks),
    site_strength: deriveSiteStrength(row, stocks, sentiment),
  }
}

function stripNotebookCitations(text: string): string {
  return text
    .replace(/[〖【]\s*(文字紀錄|投資倒數小結|完整摘要)\s*[〗】]/g, '')
    .replace(/\s*\[\d+(?:[,，\s\-–]+\d+)*\]/g, '')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function summaryLines(summary: string): string[] {
  return summary
    .replace(/\r/g, '\n')
    .split(/\n|。|；|;|\.\s+/)
    .map((line) => line.replace(/^[\s\-*#\d.、:：]+/, '').trim())
    .filter((line) => line.length >= 12)
}

function deriveUniqueInsight(summary: string, stocks: string[]): string {
  const lines = summaryLines(summary)
  const signalWords = ['風險', '機會', '催化', '估值', '需求', '庫存', '利率', '財報', '供應鏈', '現金流', 'AI', '政策']
  const picked = lines.find((line) => signalWords.some((word) => line.includes(word))) ?? lines[0]
  if (picked) return picked.slice(0, 120)
  if (stocks.length) return `本集焦點集中在 ${stocks.slice(0, 3).join(' / ')}，適合追蹤後續共識是否擴散到其他 KOL。`
  return '本集提供市場脈絡與敘事變化，可作為後續訊號交叉驗證的背景資料。'
}

function deriveSiteStrength(
  row: Record<string, unknown>,
  stocks: string[],
  sentiment: 'bullish' | 'bearish' | 'neutral',
): string {
  const kolName = String(row.kol_name ?? '此 KOL')
  const direction = sentiment === 'bullish' ? '偏多' : sentiment === 'bearish' ? '偏空' : '中性'
  const stockText = stocks.length ? stocks.slice(0, 3).join(' / ') : '市場主題'
  return `把 ${kolName} 對 ${stockText} 的${direction}語句拆成標的、方向、理由與可回測訊號，形成網站可比較的研究資料。`
}

function mapHistoryRow(row: Record<string, unknown>): ConsensusHistory {
  return {
    date: row.date instanceof Date ? row.date.toISOString().slice(0, 10) : String(row.date ?? ''),
    score: Number(row.consensus_score ?? 0),
    top_stock: String(row.top_stock ?? ''),
    sentiment_bullish: Number(row.bullish_pct ?? 0),
  }
}

function mapSignalRow(row: Record<string, unknown>): DailySignal {
  return {
    signal_date: row.signal_date instanceof Date ? row.signal_date.toISOString().slice(0, 10) : String(row.signal_date ?? ''),
    ticker: String(row.ticker ?? ''),
    name: String(row.name ?? ''),
    market: row.market as 'TW' | 'US',
    direction: row.direction as 'bullish' | 'bearish' | 'neutral',
    confidence_score: Number(row.confidence_score ?? 0),
    source_count: Number(row.source_count ?? 0),
    episode_count: Number(row.episode_count ?? 0),
    source_kols: Array.isArray(row.source_kols) ? row.source_kols as string[] : [],
    catalysts: Array.isArray(row.catalysts) ? row.catalysts as string[] : [],
    horizon: String(row.horizon ?? ''),
    thesis: String(row.thesis ?? ''),
    price_at_signal: row.price_at_signal == null ? null : Number(row.price_at_signal),
    return_1d: row.return_1d == null ? null : Number(row.return_1d),
    return_5d: row.return_5d == null ? null : Number(row.return_5d),
    return_20d: row.return_20d == null ? null : Number(row.return_20d),
  }
}

function automationFromRun(row: Record<string, unknown> | undefined): ConsensusData['automation'] {
  if (!row) return { latest_run: null, completeness_pct: 0 }
  const total = Number(row.sources_total ?? 0)
  const success = Number(row.sources_success ?? 0)
  return {
    latest_run: {
      run_id: String(row.run_id ?? ''),
      job_type: String(row.job_type ?? ''),
      mode: String(row.mode ?? ''),
      status: row.status as JobRun['status'],
      started_at: row.started_at instanceof Date ? row.started_at.toISOString() : String(row.started_at ?? ''),
      finished_at: row.finished_at instanceof Date ? row.finished_at.toISOString() : String(row.finished_at ?? ''),
      sources_total: total,
      sources_success: success,
      sources_failed: Number(row.sources_failed ?? 0),
      episodes_found: Number(row.episodes_found ?? 0),
      episodes_written: Number(row.episodes_written ?? 0),
    },
    completeness_pct: total > 0 ? Math.round((success / total) * 100) : 0,
  }
}

function emptyConsensusData(): ConsensusData {
  return {
    generated_at: new Date().toISOString(),
    date: new Date().toISOString().slice(0, 10),
    episodes_analyzed: 0,
    consensus: {
      stocks: [],
      market_sentiment: { bullish: 0, neutral: 0, bearish: 0 },
      consensus_score: 0,
      top_keywords: [],
      weekly_theme: '尚無資料',
    },
    episodes: [],
    consensus_history: [],
    signals: [],
    automation: { latest_run: null, completeness_pct: 0 },
  }
}
