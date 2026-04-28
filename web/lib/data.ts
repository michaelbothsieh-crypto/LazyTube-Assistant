import { neon } from '@neondatabase/serverless'
import { unstable_cache } from 'next/cache'
import type { ConsensusData, ConsensusHistory, Episode, Stock } from '@/types'

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
      SELECT * FROM consensus_daily ORDER BY date DESC LIMIT 1
    `

    if (!consensus) return emptyConsensusData()

    const latestDate: string = consensus.date instanceof Date
      ? consensus.date.toISOString().slice(0, 10)
      : String(consensus.date)

    const [stocks, episodes, history] = await Promise.all([
      db`
        SELECT ticker, name, market, mentions, sentiment, kols
        FROM stock_mentions
        WHERE date = ${latestDate}
        ORDER BY mentions DESC
      `,
      db`
        SELECT e.kol_id, k.kol_name, k.host, k.avatar, k.color,
               e.title, e.published, e.summary, e.sentiment,
               e.stocks_mentioned, e.report_url
        FROM episodes e
        JOIN kols k ON k.kol_id = e.kol_id
        WHERE e.analysis_date = ${latestDate}
        ORDER BY e.analyzed_at DESC
      `,
      db`
        SELECT date, consensus_score, top_keywords[1] AS top_stock, bullish_pct
        FROM consensus_daily
        ORDER BY date DESC
        LIMIT 30
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
      SELECT e.kol_id, k.kol_name, k.host, k.avatar, k.color,
             e.title, e.published, e.summary, e.sentiment,
             e.stocks_mentioned, e.report_url
      FROM episodes e
      JOIN kols k ON k.kol_id = e.kol_id
      WHERE e.kol_id = ${kolId}
      ORDER BY e.analyzed_at DESC
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
    const rows = await db`SELECT DISTINCT kol_id FROM episodes ORDER BY kol_id`
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
        WHERE sm.date = (SELECT MAX(date) FROM consensus_daily)
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
  return {
    kol_id: String(row.kol_id ?? ''),
    kol_name: String(row.kol_name ?? ''),
    host: String(row.host ?? ''),
    avatar: String(row.avatar ?? ''),
    color: String(row.color ?? '#73f1ba'),
    title: String(row.title ?? ''),
    published: row.published instanceof Date
      ? row.published.toISOString().slice(0, 10)
      : String(row.published ?? ''),
    summary: String(row.summary ?? ''),
    sentiment: row.sentiment as 'bullish' | 'bearish' | 'neutral',
    stocks_mentioned: Array.isArray(row.stocks_mentioned) ? row.stocks_mentioned as string[] : [],
    report_url: String(row.report_url ?? ''),
  }
}

function mapHistoryRow(row: Record<string, unknown>): ConsensusHistory {
  return {
    date: row.date instanceof Date ? row.date.toISOString().slice(0, 10) : String(row.date ?? ''),
    score: Number(row.consensus_score ?? 0),
    top_stock: String(row.top_stock ?? ''),
    sentiment_bullish: Number(row.bullish_pct ?? 0),
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
  }
}
