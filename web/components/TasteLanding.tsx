'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import type { ConsensusData, DailyBrief, Episode } from '@/types'
import { Activity, ChevronRight, ExternalLink, Minus, TrendDown, TrendUp, Users } from '@/components/icons'

type TasteLandingProps = {
  data: ConsensusData
}

const sentimentTone = {
  bullish: { label: '偏多', color: 'var(--gain)', Icon: TrendUp },
  neutral: { label: '中性', color: 'var(--muted)', Icon: Minus },
  bearish: { label: '偏空', color: 'var(--risk)', Icon: TrendDown },
} as const

const horizonLabel: Record<string, string> = {
  'long-term': '長線',
  swing: '波段',
  'event-driven': '事件',
  watchlist: '觀察',
}

const ignoredTickers = new Set(['GEO', 'CNC', 'RFID', 'HID', 'ASSA', 'ABLOY', 'NFC'])

function formatDateTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const parts = new Intl.DateTimeFormat('zh-TW', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).formatToParts(date)
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((item) => item.type === type)?.value ?? ''
  return `${part('month')}/${part('day')} ${part('dayPeriod')}${part('hour')}:${part('minute')}`
}

function dominantSentiment(data: ConsensusData) {
  const { bullish, bearish, neutral } = data.consensus.market_sentiment
  if (bullish >= bearish && bullish >= neutral) return 'bullish'
  if (bearish >= bullish && bearish >= neutral) return 'bearish'
  return 'neutral'
}

function formatSignalThesis(signal: ConsensusData['signals'][number]) {
  const existing = signal.thesis.trim()
  if (existing && !existing.includes('appeared across')) return existing
  return `${signal.ticker} 在 ${signal.source_count} 個來源、${signal.episode_count} 則內容中被提及，主導方向為${sentimentTone[signal.direction].label}。`
}

function readableTicker(ticker: string) {
  return ticker === 'None' ? '尚無' : ticker
}

function compactInsight(episode: Episode, maxLength = 96) {
  const text = (episode.unique_insight || episode.site_strength || episode.summary || '')
    .replace(/\s+/g, ' ')
    .trim()
  if (!text) return '尚未萃取到明確觀點，等待下一輪掃描補齊。'
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
}

function formatOutlook(episode: Episode) {
  const tickers = episode.stocks_mentioned.filter((ticker) => !ignoredTickers.has(ticker)).slice(0, 3)
  if (!tickers.length) return '觀察敘事是否擴散到更多來源。'
  return `留意 ${tickers.join(' / ')} 的催化、估值與供應鏈驗證。`
}

function DailyBriefBanner({ brief }: { brief: DailyBrief }) {
  const hasMeta = brief.source_count > 0 || brief.stock_count > 0
  const thesis = brief.thesis || brief.preview
  const themes = brief.themes?.length ? brief.themes : brief.top_stocks.slice(0, 3)
  const watchpoints = brief.watchpoints?.length ? brief.watchpoints : [brief.preview]
  const riskFlags = brief.risk_flags?.length ? brief.risk_flags : ['檢查來源共識是否被後續財報、估值與籌碼驗證。']
  const tickerCards = brief.ticker_cards?.slice(0, 3) ?? []
  const sourceDigest = brief.source_digest?.slice(0, 2) ?? []

  return (
    <section className="daily-brief-banner" aria-label="Daily podcast investment brief">
      <div className="daily-brief-copy">
        <span className="eyebrow">每日簡報</span>
        <div className="daily-brief-title-row">
          <h2>{brief.title}</h2>
          {brief.generated_at && <time>{formatDateTime(brief.generated_at)}</time>}
        </div>
        <p>{thesis}</p>
        <div className="daily-brief-meta" aria-label="Daily brief metadata">
          {hasMeta && (
            <span>{brief.source_count} 來源 / {brief.stock_count} 標的</span>
          )}
          {brief.top_stocks.map((ticker) => (
            <b key={ticker}>{ticker}</b>
          ))}
        </div>
        {tickerCards.length > 0 && (
          <div className="daily-brief-tickers" aria-label="Daily brief focus tickers">
            {tickerCards.map((card) => (
              <div key={card.ticker}>
                <b>{card.ticker}</b>
                <span>{card.source_count} 源 / {card.mention_count} 次</span>
                <small>{card.reason}</small>
              </div>
            ))}
          </div>
        )}
        {sourceDigest.length > 0 && (
          <div className="daily-brief-sources" aria-label="Daily brief source digest">
            {sourceDigest.map((source) => (
              <span key={`${source.label}-${source.title}`}>
                {source.label}：{source.stocks.slice(0, 3).join(' / ') || source.summary}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="daily-brief-research">
        <div>
          <span>主軸</span>
          <strong>{themes[0] || '等待主軸'}</strong>
          <small>{themes.slice(1).join(' / ') || '跨來源共識整理'}</small>
        </div>
        <div>
          <span>驗證</span>
          <strong>{watchpoints[0]}</strong>
        </div>
        <div>
          <span>風險</span>
          <strong>{riskFlags[0]}</strong>
        </div>
        <a className="daily-brief-open" href={brief.report_url} target="_blank" rel="noopener noreferrer">
          完整 HTML
          <ExternalLink size={16} />
        </a>
      </div>
    </section>
  )
}

export default function TasteLanding({ data }: TasteLandingProps) {
  const [filter, setFilter] = useState<'all' | 'bullish' | 'neutral' | 'bearish'>('all')
  const topStocks = data.consensus.stocks.filter((stock) => !ignoredTickers.has(stock.ticker)).slice(0, 8)
  const signals = data.signals.filter((signal) => !ignoredTickers.has(signal.ticker)).slice(0, 8)
  const episodes = data.episodes.slice(0, 16)
  const filteredEpisodes = filter === 'all' ? episodes : episodes.filter((episode) => episode.sentiment === filter)
  const direction = dominantSentiment(data)
  const directionTone = sentimentTone[direction]
  const DirectionIcon = directionTone.Icon
  const latestRun = data.automation.latest_run
  const strongestSignal = signals[0]
  const bearishSignal = signals.find((signal) => signal.direction === 'bearish')
  const crowdedStock = topStocks[0]
  const hasEffectiveSamples = data.episodes_analyzed > 0
  const marketCallValue = hasEffectiveSamples ? directionTone.label : '待資料'
  const marketCallColor = hasEffectiveSamples ? directionTone.color : 'var(--muted)'
  const showDirectionIcon = hasEffectiveSamples && direction !== 'neutral'
  const coverageText = useMemo(() => {
    if (!latestRun) return '尚未取得最新自動化執行紀錄'
    return `${latestRun.sources_success}/${latestRun.sources_total} 個來源完成，寫入 ${latestRun.episodes_written} 集`
  }, [latestRun])
  const snapshotUpdateAt = data.daily_brief?.generated_at || data.generated_at
  const snapshotCoverageText = data.daily_brief
    ? `每日簡報已整理 ${data.daily_brief.source_count} 個來源、${data.daily_brief.stock_count} 檔標的。`
    : coverageText
  const sentimentBars = [
    { key: 'bullish', label: '偏多', value: data.consensus.market_sentiment.bullish, color: 'var(--gain)' },
    { key: 'neutral', label: '中性', value: data.consensus.market_sentiment.neutral, color: 'var(--muted)' },
    { key: 'bearish', label: '偏空', value: data.consensus.market_sentiment.bearish, color: 'var(--risk)' },
  ] as const
  const marketCallDetail = data.daily_brief
    ? `${data.daily_brief.source_count} 來源 / ${data.daily_brief.stock_count} 標的`
    : hasEffectiveSamples
    ? `${data.episodes_analyzed} 集有效樣本 / 共識分數 ${data.consensus.consensus_score}`
    : '等待 Podcast scanner 寫入有效樣本'
  const dailyBriefThesis = data.daily_brief?.thesis || data.daily_brief?.preview
  const marketCallText = strongestSignal
    ? `${strongestSignal.ticker} / ${strongestSignal.name} 是今日最高信心訊號，${strongestSignal.source_count} 個來源共同指向${sentimentTone[strongestSignal.direction].label}。`
    : data.consensus.weekly_theme || '等待今日 KOL 語言訊號寫入。'
  const boardThesis = dailyBriefThesis || marketCallText
  const dailyThemes = data.daily_brief?.themes?.length
    ? data.daily_brief.themes
    : topStocks.slice(0, 3).map((stock) => `${stock.ticker} ${stock.name}`)
  const dailyWatchpoints = data.daily_brief?.watchpoints?.length
    ? data.daily_brief.watchpoints
    : [marketCallText]
  const dailyRiskFlags = data.daily_brief?.risk_flags?.length
    ? data.daily_brief.risk_flags
    : [bearishSignal ? formatSignalThesis(bearishSignal) : '目前未偵測到高信心偏空訊號。']
  const fallbackRiskHeadline = data.daily_brief ? '需驗證' : `${data.automation.completeness_pct}%`
  const riskHeadline = bearishSignal
    ? readableTicker(bearishSignal.ticker)
    : fallbackRiskHeadline
  const dailyTickerCards = data.daily_brief?.ticker_cards?.length
    ? data.daily_brief.ticker_cards
    : topStocks.slice(0, 3).map((stock) => ({
      ticker: stock.ticker,
      mention_count: stock.mentions,
      source_count: stock.kols.length,
      sources: stock.kols,
      latest_date: data.date,
      sentiment_distribution: { bullish: 0, neutral: 0, bearish: 0 },
      reason: `${stock.name} 被 ${stock.mentions} 次提及，主導方向為${sentimentTone[stock.sentiment].label}。`,
    }))

  return (
    <main className="research-shell">
      <nav className="research-nav" aria-label="Primary navigation">
        <Link href="/" className="brand-mark">KOL Signal Lab</Link>
        <div>
          <a href="#signals">訊號</a>
          <a href="#kols">KOL</a>
          <a href="#automation">自動化</a>
        </div>
      </nav>

      {data.daily_brief && <DailyBriefBanner brief={data.daily_brief} />}

      <section className={`overview-section ${data.daily_brief ? 'overview-compact' : ''}`} id="automation">
        {!data.daily_brief && (
          <article className="overview-copy">
            <p className="eyebrow">Daily decision brief</p>
            <h1>今日 KOL 語言共識：{directionTone.label}</h1>
            <p>
              {boardThesis}
            </p>
            <div className="market-pulse" aria-label="Market pulse">
              <span>今日脈搏</span>
              {topStocks.slice(0, 5).map((stock) => (
                <b key={stock.ticker}>{stock.ticker}<small>{stock.mentions}x</small></b>
              ))}
            </div>
          </article>
        )}
        <aside className="market-snapshot" aria-label="Market overview">
          <div className="snapshot-head">
            <span>市場快照</span>
            <strong style={{ color: marketCallColor }}>
              {showDirectionIcon && <DirectionIcon size={20} />}
              {marketCallValue}
            </strong>
            <small>{marketCallDetail}</small>
          </div>
          <div className="sentiment-chart" aria-label="Sentiment distribution">
            {sentimentBars.map((item) => (
              <div className="sentiment-bar-row" key={item.key}>
                <span>{item.label}</span>
                <div className="sentiment-track">
                  <i style={{ width: `${item.value}%`, background: item.color }} />
                </div>
                <strong style={{ color: item.color }}>{item.value}%</strong>
              </div>
            ))}
          </div>
          <div className="snapshot-stats">
            <div>
              <span>{data.daily_brief ? '簡報來源' : 'KOL 樣本'}</span>
              <strong>
                <Users size={16} />
                {data.daily_brief ? `${data.daily_brief.source_count} 來源` : `${data.episodes_analyzed} 集`}
              </strong>
            </div>
            <div>
              <span>{data.daily_brief ? '追蹤標的' : '掃描覆蓋'}</span>
              <strong>
                <Activity size={16} />
                {data.daily_brief ? `${data.daily_brief.stock_count} 檔` : `${data.automation.completeness_pct}%`}
              </strong>
            </div>
            <div>
              <span>更新</span>
              <strong>{formatDateTime(snapshotUpdateAt)}</strong>
            </div>
          </div>
          <p>{snapshotCoverageText}</p>
        </aside>
      </section>

      <section className="research-grid signal-workspace" id="signals" aria-label="Daily market decision board">
        <article className="panel panel-large">
          <div className="panel-head">
            <div>
              <span>核心訊號</span>
              <h2>標的、方向與信心分數集中看</h2>
            </div>
            <small>{signals.length || 0} signals</small>
          </div>
          <div className="signal-table">
            <div className="signal-table-head">
              <span>代號</span>
              <span>名稱</span>
              <span>方向</span>
              <span>信心</span>
              <span>提及</span>
              <span>節奏</span>
            </div>
            {signals.length ? signals.map((signal) => {
              const tone = sentimentTone[signal.direction]
              const mentionCount = topStocks.find((stock) => stock.ticker === signal.ticker)?.mentions ?? signal.source_count
              return (
                <Link href="#kols" className="signal-table-row" key={signal.ticker}>
                  <b>{signal.ticker}</b>
                  <span>{signal.name}</span>
                  <i style={{ color: tone.color }}>{tone.label}</i>
                  <strong>{signal.confidence_score}</strong>
                  <small>{mentionCount}x / {signal.source_count} 源</small>
                  <em>{horizonLabel[signal.horizon] ?? '觀察'}</em>
                </Link>
              )
            }) : (
              <p className="empty-note">尚無有效訊號。Podcast scanner 寫入 daily_signals 後會出現在這裡。</p>
            )}
          </div>
        </article>

        <aside className="panel signal-aside">
          <div className="panel-head">
            <div>
              <span>風險與熱度</span>
              <h2>先排除盲點，再看擁擠標的</h2>
            </div>
          </div>
          <div className="risk-list">
            <div>
              <span>主軸</span>
              <strong>{dailyThemes[0] || '尚無'}</strong>
              <p>{dailyThemes.slice(1).join(' / ') || data.consensus.weekly_theme || '等待更多來源形成主軸。'}</p>
            </div>
            <div>
              <span>驗證</span>
              <strong>{crowdedStock ? readableTicker(crowdedStock.ticker) : '觀察'}</strong>
              <p>{dailyWatchpoints[0] || '追蹤標的熱度是否延續到更多來源。'}</p>
            </div>
            <div>
              <span>風險</span>
              <strong>{riskHeadline}</strong>
              <p>{dailyRiskFlags[0] || coverageText}</p>
            </div>
          </div>
          {!data.daily_brief && dailyTickerCards.length > 0 && (
            <div className="ticker-intel-list">
              {dailyTickerCards.slice(0, 4).map((card) => (
                <div key={card.ticker}>
                  <b>{card.ticker}</b>
                  <span>{card.source_count} 源 / {card.mention_count} 次</span>
                  <p>{card.sources.slice(0, 3).join('、') || '來源待同步'}｜{card.reason}</p>
                </div>
              ))}
            </div>
          )}
        </aside>
      </section>

      <section className="panel" id="kols">
        <div className="panel-head">
          <div>
            <span>Evidence stream</span>
            <h2>支撐今日判斷的 KOL 語言證據</h2>
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
          {fallbackAvatar}
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
      <div className="insight-pill">獨到見解</div>
      <p>{compactInsight(episode)}</p>
      <div className="outlook-line">
        <span>技術瞻望</span>
        <strong>{formatOutlook(episode)}</strong>
      </div>
      <div className="ticker-row">
        {episode.stocks_mentioned.filter((ticker) => !ignoredTickers.has(ticker)).length ? episode.stocks_mentioned.filter((ticker) => !ignoredTickers.has(ticker)).slice(0, 5).map((ticker) => (
          <b key={ticker}>{ticker}</b>
        )) : <b>主題</b>}
        <i>
          詳細研究
          <ChevronRight size={14} />
        </i>
      </div>
    </Link>
  )
}
