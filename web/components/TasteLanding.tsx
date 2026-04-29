'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import type { ConsensusData, Episode } from '@/types'
import { Activity, ChevronRight, Minus, TrendDown, TrendUp, Users } from '@/components/icons'

type TasteLandingProps = {
  data: ConsensusData
}

const sentimentTone = {
  bullish: { label: '偏多', color: 'var(--gain)', Icon: TrendUp },
  neutral: { label: '中性', color: 'var(--muted)', Icon: Minus },
  bearish: { label: '偏空', color: 'var(--risk)', Icon: TrendDown },
} as const

function formatDateTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-TW', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function dominantSentiment(data: ConsensusData) {
  const { bullish, bearish, neutral } = data.consensus.market_sentiment
  if (bullish >= bearish && bullish >= neutral) return 'bullish'
  if (bearish >= bullish && bearish >= neutral) return 'bearish'
  return 'neutral'
}

export default function TasteLanding({ data }: TasteLandingProps) {
  const [filter, setFilter] = useState<'all' | 'bullish' | 'neutral' | 'bearish'>('all')
  const topStocks = data.consensus.stocks.slice(0, 8)
  const signals = data.signals.slice(0, 8)
  const episodes = data.episodes.slice(0, 16)
  const filteredEpisodes = filter === 'all' ? episodes : episodes.filter((episode) => episode.sentiment === filter)
  const direction = dominantSentiment(data)
  const directionTone = sentimentTone[direction]
  const DirectionIcon = directionTone.Icon
  const latestRun = data.automation.latest_run

  const coverageText = useMemo(() => {
    if (!latestRun) return '尚未取得最新自動化執行紀錄'
    return `${latestRun.sources_success}/${latestRun.sources_total} 個來源完成，寫入 ${latestRun.episodes_written} 集`
  }, [latestRun])

  return (
    <main className="research-shell">
      <nav className="research-nav" aria-label="Primary navigation">
        <Link href="/" className="brand-mark">PodConsensus</Link>
        <div>
          <a href="#signals">訊號</a>
          <a href="#kols">KOL</a>
          <a href="#automation">自動化</a>
        </div>
      </nav>

      <section className="research-header">
        <div>
          <p className="eyebrow">Daily podcast market brief</p>
          <h1>每日 Podcast 市場研究報告</h1>
          <p>
            將最近兩天內的 KOL 節目整理成市場方向、提及標的、獨到見解與可追蹤訊號。
            每張卡片都把原始語句提煉成網站可比較、可累積、可回測的研究資料。
          </p>
        </div>
        <aside className="run-card" id="automation">
          <span>自動化覆蓋率</span>
          <strong>{data.automation.completeness_pct}%</strong>
          <p>{coverageText}</p>
          <small>首頁只呈現最近兩天內的資料；若 scanner 沒有寫入新集，這裡會明確變少而不是回填舊內容。</small>
        </aside>
      </section>

      <section className="summary-strip" aria-label="Daily summary">
        <div>
          <span>報告日期</span>
          <strong>{data.date}</strong>
          <small>更新 {formatDateTime(data.generated_at)}</small>
        </div>
        <div>
          <span>市場方向</span>
          <strong style={{ color: directionTone.color }}>
            <DirectionIcon size={18} />
            {directionTone.label}
          </strong>
          <small>
            多 {data.consensus.market_sentiment.bullish}% / 中 {data.consensus.market_sentiment.neutral}% / 空 {data.consensus.market_sentiment.bearish}%
          </small>
        </div>
        <div>
          <span>KOL 樣本</span>
          <strong>
            <Users size={18} />
            {data.episodes_analyzed} 集
          </strong>
          <small>來自目前啟用的 RSS 來源</small>
        </div>
        <div>
          <span>共識分數</span>
          <strong>
            <Activity size={18} />
            {data.consensus.consensus_score}
          </strong>
          <small>{data.consensus.weekly_theme || '等待最新 podcast scanner 寫入資料'}</small>
        </div>
      </section>

      <section className="research-grid" id="signals">
        <article className="panel panel-large">
          <div className="panel-head">
            <div>
              <span>今日可追蹤訊號</span>
              <h2>把多位 KOL 的語句收斂成可比較的投資線索</h2>
            </div>
            <small>{signals.length || 0} signals</small>
          </div>
          <div className="signal-table">
            <div className="signal-table-head">
              <span>Ticker</span>
              <span>Name</span>
              <span>Direction</span>
              <span>Confidence</span>
              <span>Sources</span>
            </div>
            {signals.length ? signals.map((signal) => {
              const tone = sentimentTone[signal.direction]
              return (
                <Link href="#kols" className="signal-table-row" key={signal.ticker}>
                  <b>{signal.ticker}</b>
                  <span>{signal.name}</span>
                  <i style={{ color: tone.color }}>{tone.label}</i>
                  <strong>{signal.confidence_score}</strong>
                  <small>{signal.source_count}</small>
                </Link>
              )
            }) : (
              <p className="empty-note">尚無最近兩天內的訊號。Podcast scanner 寫入 daily_signals 後會出現在這裡。</p>
            )}
          </div>
        </article>

        <aside className="panel">
          <div className="panel-head">
            <div>
              <span>提及熱度</span>
              <h2>標的排行</h2>
            </div>
          </div>
          <div className="rank-list">
            {topStocks.map((stock, index) => {
              const tone = sentimentTone[stock.sentiment]
              return (
                <div className="rank-row" key={stock.ticker}>
                  <b>{index + 1}</b>
                  <span>{stock.ticker}</span>
                  <small>{stock.name}</small>
                  <strong style={{ color: tone.color }}>{stock.mentions}x</strong>
                </div>
              )
            })}
          </div>
        </aside>
      </section>

      <section className="panel" id="kols">
        <div className="panel-head">
          <div>
            <span>KOL 研究樣本</span>
            <h2>每個 KOL 的獨到見解與可產品化語句</h2>
          </div>
          <div className="filter-tabs compact-tabs">
            {(['all', 'bullish', 'neutral', 'bearish'] as const).map((item) => (
              <button key={item} type="button" className={filter === item ? 'is-active' : ''} onClick={() => setFilter(item)}>
                {item === 'all' ? '全部' : sentimentTone[item].label}
              </button>
            ))}
          </div>
        </div>
        <div className="kol-report-grid">
          {filteredEpisodes.map((episode, index) => (
            <EpisodeCard key={`${episode.kol_id}-${episode.title}-${index}`} episode={episode} />
          ))}
        </div>
      </section>
    </main>
  )
}

function EpisodeCard({ episode }: { episode: Episode }) {
  const tone = sentimentTone[episode.sentiment]
  const Icon = tone.Icon
  const fallbackAvatar = episode.kol_name.slice(0, 1) || '?'

  return (
    <Link href={`/kol/${episode.kol_id}`} className="kol-report-card">
      <div className="kol-report-top">
        <div className="kol-avatar" style={{ color: episode.color, borderColor: `${episode.color}66`, background: `${episode.color}18` }}>
          {episode.avatar || fallbackAvatar}
        </div>
        <div>
          <strong>{episode.kol_name}</strong>
          <small>{episode.host || 'Podcast'} | {episode.published}</small>
        </div>
        <span style={{ color: tone.color }}>
          <Icon size={14} />
          {tone.label}
        </span>
      </div>
      <h3>{episode.title}</h3>
      <div className="kol-insight-block">
        <span>獨到見解</span>
        <p>{episode.unique_insight}</p>
      </div>
      <div className="kol-insight-block site-strength">
        <span>網站強項</span>
        <p>{episode.site_strength}</p>
      </div>
      <div className="ticker-row">
        {episode.stocks_mentioned.slice(0, 5).map((ticker) => (
          <b key={ticker}>{ticker}</b>
        ))}
        <i>
          詳細研究
          <ChevronRight size={14} />
        </i>
      </div>
    </Link>
  )
}
