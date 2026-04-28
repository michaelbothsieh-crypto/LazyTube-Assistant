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

function financePreview(summary: string) {
  const markers = ['【投資倒數小結】', '投資倒數小結', '投資小結', '市場重點']
  const markerIndex = markers
    .map((marker) => summary.indexOf(marker))
    .filter((index) => index >= 0)
    .sort((a, b) => a - b)[0]
  const source = markerIndex == null ? summary : summary.slice(markerIndex)
  return source.replace(/\s+/g, ' ').trim()
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
          <a href="#automation">資料狀態</a>
        </div>
      </nav>

      <section className="research-header">
        <div>
          <p className="eyebrow">Daily podcast market brief</p>
          <h1>每日 Podcast 市場研究報告</h1>
          <p>
            將 Podcast scanner 蒐集到的 KOL 節目整理成市場方向、提及標的、可追蹤訊號與資料更新狀態。
            這裡呈現網站資料庫的最新結果，不會每日主動推送 Telegram。
          </p>
        </div>
        <aside className="run-card" id="automation">
          <span>資料狀態</span>
          <strong>{data.automation.completeness_pct}%</strong>
          <p>{coverageText}</p>
          <small>網頁快取約 5 分鐘更新一次；手動執行 Actions 後會在下一次重建時反映。</small>
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
          <span>研究樣本</span>
          <strong>
            <Users size={18} />
            {data.episodes_analyzed} 集
          </strong>
          <small>來自目前啟用的 KOL RSS</small>
        </div>
        <div>
          <span>訊號分數</span>
          <strong>
            <Activity size={18} />
            {data.consensus.consensus_score}
          </strong>
          <small>{data.consensus.weekly_theme || '等待更多資料形成主題'}</small>
        </div>
      </section>

      <section className="research-grid" id="signals">
        <article className="panel panel-large">
          <div className="panel-head">
            <div>
              <span>今日可追蹤訊號</span>
              <h2>以來源數、集數與信心分數排序</h2>
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
              <p className="empty-note">尚無今日訊號。Podcast scanner 寫入 daily_signals 後會出現在這裡。</p>
            )}
          </div>
        </article>

        <aside className="panel">
          <div className="panel-head">
            <div>
              <span>高頻標的</span>
              <h2>今日提及排行</h2>
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
            <h2>點進去會看到同一集節目的詳細筆記</h2>
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
      <p>{financePreview(episode.summary) || '尚無摘要內容'}</p>
      <div className="ticker-row">
        {episode.stocks_mentioned.slice(0, 5).map((ticker) => (
          <b key={ticker}>{ticker}</b>
        ))}
        <i>
          查看筆記
          <ChevronRight size={14} />
        </i>
      </div>
    </Link>
  )
}
