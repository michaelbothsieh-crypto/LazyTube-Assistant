export interface Stock {
  ticker: string
  name: string
  market: 'TW' | 'US'
  mentions: number
  sentiment: 'bullish' | 'bearish' | 'neutral'
  kols: string[]
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
}

export interface ConsensusHistory {
  date: string
  score: number
  top_stock: string
  sentiment_bullish: number
}

export interface ConsensusData {
  generated_at: string
  date: string
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
}
