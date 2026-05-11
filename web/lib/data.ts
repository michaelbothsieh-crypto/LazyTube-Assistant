import { neon } from '@neondatabase/serverless'
import { unstable_cache } from 'next/cache'
import fallbackLatest from '@/data/latest.json'
import type { ConsensusData, ConsensusHistory, DailyBrief, DailySignal, Episode, JobRun, Stock } from '@/types'

const DAILY_BRIEF_REDIS_KEY = 'daily_podcast_brief_latest'

const configuredKolFallbacks: Record<string, Pick<Episode, 'kol_name' | 'host' | 'avatar' | 'color'>> = {
  gooaye: { kol_name: '股癌 Podcast', host: '謝孟恭', avatar: '', color: '#4f8cff' },
  yutin: { kol_name: '游庭皓的財經皓角', host: '游庭皓', avatar: '', color: '#3ddc97' },
  macromicro: { kol_name: 'MacroMicro 財經M平方', host: 'Rachel', avatar: '', color: '#a78bfa' },
  billkitchen: { kol_name: '比爾的財經廚房', host: '比爾', avatar: '', color: '#f8b84e' },
  zhaohualink: { kol_name: '兆華與股惑仔', host: '李兆華', avatar: '', color: '#ff6b6b' },
  caalaw: { kol_name: '財報狗', host: 'Jeff & Sky', avatar: '', color: '#2dd4bf' },
  morales: { kol_name: '呱吉的股市觀察', host: '邱威傑', avatar: '', color: '#7ddc6f' },
  shenghong: { kol_name: '升鴻投資', host: '升鴻', avatar: '', color: '#42c6ff' },
  richie: { kol_name: '瑞奇的投資觀點', host: 'Richie', avatar: '', color: '#ffd166' },
  stockfeel: { kol_name: '股感知識庫', host: '股感團隊', avatar: '', color: '#63d297' },
  technews: { kol_name: '科技新報', host: 'TechNews', avatar: '', color: '#38bdf8' },
  inside: { kol_name: 'INSIDE', host: 'INSIDE 編輯部', avatar: '', color: '#c084fc' },
  meet: { kol_name: '創業小聚', host: 'Meet 創業小聚', avatar: '', color: '#fb923c' },
  ithome: { kol_name: 'iThome', host: 'iThome', avatar: '', color: '#94a3b8' },
  techorange: { kol_name: 'TechOrange 科技報橘', host: 'TechOrange', avatar: '', color: '#ff9f43' },
  managertoday: { kol_name: '經理人', host: '經理人月刊', avatar: '', color: '#6ee7b7' },
}

export function getConfiguredKolIds(): string[] {
  return Object.keys(configuredKolFallbacks)
}

function sql() {
  const url = process.env.DATABASE_URL
  if (!url) return null
  return neon(url)
}

export const getLatestData = _getLatestData

async function _getLatestData(): Promise<ConsensusData> {
  const dailyBrief = await getLatestDailyBrief()
  const db = sql()
  if (!db) {
    const fallback = fallbackConsensusData()
    return { ...fallback, daily_brief: dailyBrief ?? fallback.daily_brief }
  }

  try {
    const [consensus] = await db`
      SELECT *
      FROM consensus_daily
      ORDER BY date DESC
      LIMIT 1
    `

    if (!consensus) return { ...emptyConsensusData(), daily_brief: dailyBrief }

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
          WHERE e.published >= ${latestDateValue}::date - INTERVAL '2 days'
            AND e.published <= ${latestDateValue}::date + INTERVAL '1 day'
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
          ORDER BY COALESCE(NULLIF(rss_url, ''), kol_id),
                   CASE WHEN kol_id ~ '^[0-9a-f]{10}$' THEN 1 ELSE 0 END,
                   added_at ASC
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
      daily_brief: dailyBrief,
    }
  } catch {
    const fallback = fallbackConsensusData()
    return { ...fallback, daily_brief: dailyBrief ?? fallback.daily_brief }
  }
}

async function getLatestDailyBrief(): Promise<DailyBrief | null> {
  const redisUrl = process.env.UPSTASH_REDIS_REST_URL
  const redisToken = process.env.UPSTASH_REDIS_REST_TOKEN
  if (!redisUrl || !redisToken) return null

  try {
    const response = await fetch(redisUrl, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${redisToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(['GET', DAILY_BRIEF_REDIS_KEY]),
      next: { revalidate: 300 },
    })
    if (!response.ok) return null
    const data = await response.json() as { result?: unknown }
    const raw = typeof data.result === 'string' ? data.result : ''
    if (!raw) return null
    return normalizeDailyBrief(JSON.parse(raw))
  } catch {
    return null
  }
}

function normalizeDailyBrief(value: unknown): DailyBrief | null {
  if (!value || typeof value !== 'object') return null
  const record = value as Record<string, unknown>
  const reportUrl = String(record.report_url ?? '')
  const preview = String(record.preview ?? '').trim()
  if (!reportUrl || !preview) return null

  return {
    title: String(record.title ?? '每日 Podcast 投資統整'),
    report_url: reportUrl,
    preview,
    generated_at: String(record.generated_at ?? ''),
    source_count: Number(record.source_count ?? 0),
    stock_count: Number(record.stock_count ?? 0),
    top_stocks: Array.isArray(record.top_stocks)
      ? record.top_stocks.map((stock) => String(stock)).filter(Boolean).slice(0, 8)
      : [],
  }
}

export async function getEpisodeByKolId(kolId: string): Promise<Episode | null> {
  const db = sql()
  if (!db) return fallbackEpisodeByKolId(kolId)

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
        ORDER BY COALESCE(NULLIF(k.rss_url, ''), k.kol_id),
                 CASE WHEN k.kol_id ~ '^[0-9a-f]{10}$' THEN 1 ELSE 0 END,
                 k.added_at ASC
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
    return rows.length ? mapEpisodeRow(rows[0]) : fallbackEpisodeByKolId(kolId)
  } catch {
    return fallbackEpisodeByKolId(kolId)
  }
}

export async function getAllKolIds(): Promise<string[]> {
  const db = sql()
  if (!db) return getFallbackKolIds()

  try {
    const rows = await db`
      WITH canonical_kols AS (
        SELECT DISTINCT ON (COALESCE(NULLIF(rss_url, ''), kol_id))
               COALESCE(NULLIF(rss_url, ''), kol_id) AS source_key,
               kol_id
        FROM kols
        WHERE POSITION('://' IN kol_name) = 0
        ORDER BY COALESCE(NULLIF(rss_url, ''), kol_id),
                 CASE WHEN kol_id ~ '^[0-9a-f]{10}$' THEN 1 ELSE 0 END,
                 added_at ASC
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
    return mergeKolIds(rows.map((row) => row.kol_id as string))
  } catch {
    return getFallbackKolIds()
  }
}

export const getLatestStocks = unstable_cache(
  async (): Promise<Stock[]> => {
    const db = sql()
    if (!db) return fallbackConsensusData().consensus.stocks

    try {
      const rows = await db`
        SELECT sm.ticker, sm.name, sm.market, sm.mentions, sm.sentiment, sm.kols
        FROM stock_mentions sm
        WHERE sm.date = (
          SELECT MAX(date)
          FROM stock_mentions
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
      return fallbackConsensusData().consensus.stocks
    }
  },
  ['latest-stocks'],
  { revalidate: 300 },
)

export const getConsensusHistory = unstable_cache(
  async (): Promise<ConsensusHistory[]> => {
    const db = sql()
    if (!db) return fallbackConsensusData().consensus_history

    try {
      const rows = await db`
        SELECT date, consensus_score, top_keywords[1] AS top_stock, bullish_pct
        FROM consensus_daily
        ORDER BY date ASC
        LIMIT 30
      `
      return rows.map(mapHistoryRow)
    } catch {
      return fallbackConsensusData().consensus_history
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
    daily_brief: null,
  }
}

function fallbackConsensusData(): ConsensusData {
  const data = fallbackLatest as unknown as ConsensusData
  return {
    ...emptyConsensusData(),
    ...data,
    consensus: {
      ...emptyConsensusData().consensus,
      ...data.consensus,
    },
    episodes: (data.episodes ?? []).map((episode) => ({
      ...episode,
      unique_insight: episode.unique_insight || deriveUniqueInsight(episode.summary || '', episode.stocks_mentioned || []),
      site_strength: episode.site_strength || deriveSiteStrength(episode as unknown as Record<string, unknown>, episode.stocks_mentioned || [], episode.sentiment || 'neutral'),
    })),
    consensus_history: data.consensus_history ?? [],
    signals: data.signals ?? [],
    automation: data.automation ?? { latest_run: null, completeness_pct: 0 },
    daily_brief: data.daily_brief ?? null,
  }
}

function fallbackEpisodeByKolId(kolId: string): Episode | null {
  const fallbackEpisode = fallbackConsensusData().episodes.find((episode) => episode.kol_id === kolId)
  if (fallbackEpisode) return fallbackEpisode

  const kol = configuredKolFallbacks[kolId]
  if (!kol) return null

  const summary = '這個 KOL 已在網站來源清單中，但目前 production 環境尚未取得對應的最新分析內容。請回首頁查看其他已同步來源，或等待下一輪 scanner 寫入資料。'
  return {
    kol_id: kolId,
    ...kol,
    title: `${kol.kol_name} 最新分析待同步`,
    published: new Date().toISOString().slice(0, 10),
    summary,
    sentiment: 'neutral',
    stocks_mentioned: [],
    report_url: '',
    unique_insight: summary,
    site_strength: `${kol.kol_name} 已納入來源監控，等待最新可分析內容同步。`,
  }
}

function getFallbackKolIds(): string[] {
  return mergeKolIds(fallbackConsensusData().episodes.map((episode) => episode.kol_id))
}

function mergeKolIds(ids: string[]): string[] {
  return Array.from(new Set([
    ...ids,
    ...fallbackConsensusData().episodes.map((episode) => episode.kol_id),
    ...getConfiguredKolIds(),
  ])).sort()
}
