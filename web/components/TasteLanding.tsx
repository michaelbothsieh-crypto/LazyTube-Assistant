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

const extractionSteps = [
  { label: '語句收集', value: 'RSS + episode', detail: '每日 10:30 掃描近期 KOL 與科技商業 RSS，保留來源與集數脈絡。' },
  { label: '觀點萃取', value: 'thesis', detail: '把敘事拆成標的、方向、理由、風險與催化條件。' },
  { label: '共識建模', value: 'signal graph', detail: '用跨來源重複度與信心分數呈現語言力量的擴散。' },
] as const

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

  return (
    <section className="daily-brief-banner" aria-label="Daily podcast investment brief">
      <div className="daily-brief-copy">
        <span className="eyebrow">每日簡報</span>
        <div className="daily-brief-title-row">
          <h2>{brief.title}</h2>
          {brief.generated_at && <time>{formatDateTime(brief.generated_at)}</time>}
        </div>
        <p>{brief.preview}</p>
        <div className="daily-brief-meta" aria-label="Daily brief metadata">
          {hasMeta && (
            <span>{brief.source_count} 來源 / {brief.stock_count} 標的</span>
          )}
          {brief.top_stocks.map((ticker) => (
            <b key={ticker}>{ticker}</b>
          ))}
        </div>
      </div>
      <a className="daily-brief-open" href={brief.report_url} target="_blank" rel="noopener noreferrer">
        查看完整 HTML
        <ExternalLink size={16} />
      </a>
    </section>
  )
}

export default function TasteLanding({ data }: TasteLandingProps) {
  const [filter, setFilter] = useState<'all' | 'bullish' | 'neutral' | 'bearish'>('all')
  const topStocks = data.consensus.stocks.filter((stock) => !ignoredTickers.has(stock.ticker)).slice(0, 8)
  const signals = data.signals.filter((signal) => !ignoredTickers.has(signal.ticker)).slice(0, 8)
  const topDecisionSignals = signals.slice(0, 3)
  const episodes = data.episodes.slice(0, 16)
  const filteredEpisodes = filter === 'all' ? episodes : episodes.filter((episode) => episode.sentiment === filter)
  const featuredInsights = episodes
    .filter((episode) => episode.unique_insight)
    .slice(0, 3)
  const marqueeEpisodes = (featuredInsights.length ? featuredInsights : episodes).slice(0, 10)
  const direction = dominantSentiment(data)
  const directionTone = sentimentTone[direction]
  const DirectionIcon = directionTone.Icon
  const latestRun = data.automation.latest_run
  const strongestSignal = topDecisionSignals[0]
  const bearishSignal = signals.find((signal) => signal.direction === 'bearish')
  const crowdedStock = topStocks[0]
  const hasEffectiveSamples = data.episodes_analyzed > 0
  const marketCallValue = hasEffectiveSamples ? directionTone.label : '待資料'
  const marketCallColor = hasEffectiveSamples ? directionTone.color : 'var(--muted)'
  const marketCallDetail = hasEffectiveSamples
    ? `${data.episodes_analyzed} 集有效樣本 / 共識分數 ${data.consensus.consensus_score}`
    : '等待 Podcast scanner 寫入有效樣本'
  const marketCallText = strongestSignal
    ? `${strongestSignal.ticker} / ${strongestSignal.name} 是今日最高信心訊號，${strongestSignal.source_count} 個來源共同指向${sentimentTone[strongestSignal.direction].label}。`
    : data.consensus.weekly_theme || '等待今日 KOL 語言訊號寫入。'

  const coverageText = useMemo(() => {
    if (!latestRun) return '尚未取得最新自動化執行紀錄'
    return `${latestRun.sources_success}/${latestRun.sources_total} 個來源完成，寫入 ${latestRun.episodes_written} 集`
  }, [latestRun])

  return (
    <main className="research-shell">
      <nav className="research-nav" aria-label="Primary navigation">
        <Link href="/" className="brand-mark">KOL Signal Lab</Link>
        <div>
          <a href="#extraction">架構</a>
          <a href="#signals">訊號</a>
          <a href="#kols">KOL</a>
          <a href="#automation">自動化</a>
        </div>
      </nav>

      {data.daily_brief && <DailyBriefBanner brief={data.daily_brief} />}

      <section className="research-header">
        <div>
          <p className="eyebrow">Daily decision brief</p>
          <h1>今日 KOL 語言共識：{directionTone.label}</h1>
          <p>
            {marketCallText}
          </p>
          <div className="market-pulse" aria-label="Market pulse">
            <span>今日脈搏</span>
            {topStocks.slice(0, 5).map((stock) => (
              <b key={stock.ticker}>{stock.ticker}<small>{stock.mentions}x</small></b>
            ))}
          </div>
        </div>
        <aside className="run-card" id="automation">
          <span>Market call</span>
          <strong style={{ color: marketCallColor }}>
            <DirectionIcon size={26} />
            {marketCallValue}
          </strong>
          <p>{marketCallDetail}</p>
          <small>每日台北 10:30 掃描；首頁顯示最近一次有效資料。</small>
        </aside>
      </section>

      {marqueeEpisodes.length > 0 && (
        <section className="kol-marquee" aria-label="KOL precision viewpoints">
          <div className="kol-marquee-label">
            <span>Live KOL tape</span>
            <strong>精準觀點</strong>
          </div>
          <div className="kol-marquee-window">
            <div className="kol-marquee-track">
              {[...marqueeEpisodes, ...marqueeEpisodes].map((episode, index) => (
                <Link href={`/kol/${episode.kol_id}`} className="kol-marquee-item" key={`${episode.kol_id}-${index}`}>
                  <b>{episode.kol_name}</b>
                  <span>{compactInsight(episode, 88)}</span>
                  <i>{formatOutlook(episode)}</i>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="decision-board" id="signals" aria-label="Daily market decision board">
        <article className="panel panel-large">
          <div className="panel-head">
            <div>
              <span>今日必看訊號</span>
              <h2>先看最高信心標的，再決定是否下鑽證據</h2>
            </div>
            <small>{topDecisionSignals.length} priority signals</small>
          </div>
          <div className="priority-signal-list">
            {topDecisionSignals.length ? topDecisionSignals.map((signal, index) => {
              const tone = sentimentTone[signal.direction]
              return (
                <Link href="#kols" className="priority-signal" key={signal.ticker}>
                  <b>{String(index + 1).padStart(2, '0')}</b>
                  <div>
                    <span>{signal.ticker}</span>
                    <strong>{signal.name}</strong>
                    <p>{formatSignalThesis(signal)}</p>
                  </div>
                  <i style={{ color: tone.color }}>{tone.label}</i>
                  <em>{signal.confidence_score}</em>
                  <small>{signal.source_count} 來源</small>
                </Link>
              )
            }) : (
              <p className="empty-note">尚無有效訊號。Podcast scanner 寫入 daily_signals 後會出現在這裡。</p>
            )}
          </div>
        </article>

        <aside className="panel risk-panel">
          <div className="panel-head">
            <div>
              <span>風險雷達</span>
              <h2>今日要先排除的盲點</h2>
            </div>
          </div>
          <div className="risk-list">
            <div>
              <span>反向訊號</span>
              <strong>{bearishSignal ? readableTicker(bearishSignal.ticker) : '尚無'}</strong>
              <p>{bearishSignal ? formatSignalThesis(bearishSignal) : '目前未偵測到高信心偏空訊號。'}</p>
            </div>
            <div>
              <span>擁擠標的</span>
              <strong>{crowdedStock ? crowdedStock.ticker : '尚無'}</strong>
              <p>{crowdedStock ? `${crowdedStock.mentions} 次提及，方向為 ${sentimentTone[crowdedStock.sentiment].label}。` : '尚無標的熱度資料。'}</p>
            </div>
            <div>
              <span>資料覆蓋</span>
              <strong>{data.automation.completeness_pct}%</strong>
              <p>{coverageText}</p>
            </div>
          </div>
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
          <span>自動化</span>
          <strong>
            <Activity size={18} />
            {data.automation.completeness_pct}%
          </strong>
          <small>{coverageText}</small>
        </div>
      </section>

      <section className="language-lab" id="extraction" aria-label="KOL language extraction architecture">
        <div className="panel-head">
          <div>
            <span>萃取架構</span>
            <h2>從一句話到可追蹤訊號</h2>
          </div>
          <small>scan 10:30 TPE</small>
        </div>
        <div className="pipeline-grid">
          {extractionSteps.map((step, index) => (
            <div className="pipeline-step" key={step.label}>
              <b>{String(index + 1).padStart(2, '0')}</b>
              <span>{step.label}</span>
              <strong>{step.value}</strong>
              <p>{step.detail}</p>
            </div>
          ))}
        </div>
        <div className="insight-grid">
          {(featuredInsights.length ? featuredInsights : episodes.slice(0, 3)).map((episode, index) => (
            <Link href={`/kol/${episode.kol_id}`} className="insight-card" key={`${episode.kol_id}-${index}`}>
              <span>{episode.kol_name}</span>
              <p>{episode.unique_insight || episode.summary.replace(/\s+/g, ' ').trim() || '等待最新節目寫入可萃取觀點。'}</p>
            </Link>
          ))}
        </div>
      </section>

      <section className="research-grid">
        <article className="panel panel-large">
          <div className="panel-head">
            <div>
              <span>完整訊號表</span>
              <h2>用同一套欄位比較每日投資線索</h2>
            </div>
            <small>{signals.length || 0} signals</small>
          </div>
          <div className="signal-table">
            <div className="signal-table-head">
              <span>代號</span>
              <span>名稱</span>
              <span>方向</span>
              <span>信心</span>
              <span>來源</span>
              <span>節奏</span>
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
                  <em>{horizonLabel[signal.horizon] ?? '觀察'}</em>
                </Link>
              )
            }) : (
              <p className="empty-note">尚無有效訊號。Podcast scanner 寫入 daily_signals 後會出現在這裡。</p>
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
