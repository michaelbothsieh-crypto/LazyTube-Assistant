import { neon } from '@neondatabase/serverless'
import { unstable_cache } from 'next/cache'
import type { ConsensusData, Episode, Stock, ConsensusHistory } from '@/types'

function sql() {
  const url = process.env.DATABASE_URL
  if (!url) throw new Error('DATABASE_URL 未設定')
  return neon(url)
}

// 一次 ISR 週期（300s）內不管幾個頁面呼叫，只打一次 DB
export const getLatestData = unstable_cache(
  _getLatestData,
  ['latest-consensus-data'],
  { revalidate: 300, tags: ['consensus'] }
)

async function _getLatestData(): Promise<ConsensusData> {
  const db = sql()

  // 取最新一天的共識資料
  const [consensus] = await db`
    SELECT * FROM consensus_daily ORDER BY date DESC LIMIT 1
  `

  if (!consensus) {
    return emptyConsensusData()
  }

  const latestDate: string = consensus.date instanceof Date
    ? consensus.date.toISOString().slice(0, 10)
    : String(consensus.date)

  // 平行查詢：股票 + 集數 + 歷史
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
      stocks: stocks.map((s): Stock => ({
        ticker: s.ticker,
        name: s.name,
        market: s.market as 'TW' | 'US',
        mentions: Number(s.mentions),
        sentiment: s.sentiment as 'bullish' | 'bearish' | 'neutral',
        kols: s.kols ?? [],
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
    episodes: episodes.map((e): Episode => ({
      kol_id: e.kol_id,
      kol_name: e.kol_name,
      host: e.host ?? '',
      avatar: e.avatar ?? '🎙️',
      color: e.color ?? '#6366f1',
      title: e.title,
      published: e.published instanceof Date
        ? e.published.toISOString().slice(0, 10)
        : String(e.published ?? ''),
      summary: e.summary ?? '',
      sentiment: e.sentiment as 'bullish' | 'bearish' | 'neutral',
      stocks_mentioned: e.stocks_mentioned ?? [],
      report_url: e.report_url ?? '',
    })),
    consensus_history: [...history].reverse().map((h): ConsensusHistory => ({
      date: h.date instanceof Date
        ? h.date.toISOString().slice(0, 10)
        : String(h.date),
      score: Number(h.consensus_score),
      top_stock: h.top_stock ?? '',
      sentiment_bullish: Number(h.bullish_pct),
    })),
  }
}

export async function getEpisodeByKolId(kolId: string): Promise<Episode | null> {
  const db = sql()
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
  if (!rows.length) return null
  const e = rows[0]
  return {
    kol_id: e.kol_id,
    kol_name: e.kol_name,
    host: e.host ?? '',
    avatar: e.avatar ?? '🎙️',
    color: e.color ?? '#6366f1',
    title: e.title,
    published: e.published instanceof Date
      ? e.published.toISOString().slice(0, 10)
      : String(e.published ?? ''),
    summary: e.summary ?? '',
    sentiment: e.sentiment as 'bullish' | 'bearish' | 'neutral',
    stocks_mentioned: e.stocks_mentioned ?? [],
    report_url: e.report_url ?? '',
  }
}

export async function getAllKolIds(): Promise<string[]> {
  const db = sql()
  const rows = await db`SELECT DISTINCT kol_id FROM episodes ORDER BY kol_id`
  return rows.map(r => r.kol_id as string)
}

// 取最新共識日的股票列表（供 KOL 詳細頁查關聯）
export async function getLatestStocks(): Promise<Stock[]> {
  const db = sql()
  const rows = await db`
    SELECT sm.ticker, sm.name, sm.market, sm.mentions, sm.sentiment, sm.kols
    FROM stock_mentions sm
    WHERE sm.date = (SELECT MAX(date) FROM consensus_daily)
    ORDER BY sm.mentions DESC
  `
  return rows.map((s): Stock => ({
    ticker: s.ticker,
    name: s.name,
    market: s.market as 'TW' | 'US',
    mentions: Number(s.mentions),
    sentiment: s.sentiment as 'bullish' | 'bearish' | 'neutral',
    kols: s.kols ?? [],
  }))
}

export async function getConsensusHistory(): Promise<ConsensusHistory[]> {
  const db = sql()
  const rows = await db`
    SELECT date, consensus_score, top_keywords[1] AS top_stock, bullish_pct
    FROM consensus_daily
    ORDER BY date ASC
    LIMIT 30
  `
  return rows.map((h): ConsensusHistory => ({
    date: h.date instanceof Date
      ? h.date.toISOString().slice(0, 10)
      : String(h.date),
    score: Number(h.consensus_score),
    top_stock: h.top_stock ?? '',
    sentiment_bullish: Number(h.bullish_pct),
  }))
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
