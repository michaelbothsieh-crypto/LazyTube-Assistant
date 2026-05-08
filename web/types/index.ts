export interface Stock {
  ticker: string
  name: string
  market: 'TW' | 'US'
  mentions: number
  sentiment: 'bullish' | 'bearish' | 'neutral'
  kols: string[]
}

export interface DailySignal {
  signal_date: string
  ticker: string
  name: string
  market: 'TW' | 'US'
  direction: 'bullish' | 'bearish' | 'neutral'
  confidence_score: number
  source_count: number
  episode_count: number
  source_kols: string[]
  catalysts: string[]
  horizon: string
  thesis: string
  price_at_signal: number | null
  return_1d: number | null
  return_5d: number | null
  return_20d: number | null
}

export interface JobRun {
  run_id: string
  job_type: string
  mode: string
  status: 'running' | 'success' | 'partial' | 'failed'
  started_at: string
  finished_at: string
  sources_total: number
  sources_success: number
  sources_failed: number
  episodes_found: number
  episodes_written: number
}

export interface Episode {
  kol_id: string
  kol_name: string
  host: string
  avatar: string
  color: string
  title: string
  published: string
  summary: string
  sentiment: 'bullish' | 'bearish' | 'neutral'
  stocks_mentioned: string[]
  report_url: string
  unique_insight: string
  site_strength: string
}

export interface ConsensusHistory {
  date: string
  score: number
  top_stock: string
  sentiment_bullish: number
}

export interface DailyBrief {
  title: string
  report_url: string
  preview: string
  generated_at: string
  source_count: number
  stock_count: number
  top_stocks: string[]
}

export interface ConsensusData {
  generated_at: string
  date: string
  daily_brief: DailyBrief | null
  episodes_analyzed: number
  consensus: {
    stocks: Stock[]
    market_sentiment: { bullish: number; bearish: number; neutral: number }
    consensus_score: number
    top_keywords: string[]
    weekly_theme: string
  }
  episodes: Episode[]
  consensus_history: ConsensusHistory[]
  signals: DailySignal[]
  automation: {
    latest_run: JobRun | null
    completeness_pct: number
  }
}
