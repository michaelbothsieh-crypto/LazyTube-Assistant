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

const extractionSteps = [
  { label: '語句收集', value: 'RSS + episode', detail: '每日 10:30 掃描近期 KOL 節目，保留來源與集數脈絡。' },
  { label: '觀點萃取', value: 'thesis', detail: '把敘事拆成標的、方向、理由、風險與催化條件。' },
  { label: '共識建模', value: 'signal graph', detail: '用跨 KOL 重複度與信心分數呈現語言力量的擴散。' },
] as const

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
  const topDecisionSignals = signals.slice(0, 3)
  const episodes = data.episodes.slice(0, 16)
  const filteredEpisodes = filter === 'all' ? episodes : episodes.filter((episode) => episode.sentiment === filter)
  const featuredInsights = episodes
    .filter((episode) => episode.unique_insight)
    .slice(0, 3)
  const direction = dominantSentiment(data)
  const directionTone = sentimentTone[direction]
  const DirectionIcon = directionTone.Icon
  const latestRun = data.automation.latest_run
  const strongestSignal = topDecisionSignals[0]
  const bearishSignal = signals.find((signal) => signal.direction === 'bearish')
  const crowdedStock = topStocks[0]
  const marketCallText = strongestSignal
    ? `${strongestSignal.ticker} / ${strongestSignal.name} 是今日最高信心訊號，${strongestSignal.source_count} 位 KOL 共同指向${sentimentTone[strongestSignal.direction].label}。`
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

      <section className="research-header">
        <div>
          <p className="eyebrow">Daily decision brief</p>
          <h1>今日 KOL 語言共識：{directionTone.label}</h1>
          <p>
            {marketCallText}
          </p>
        </div>
        <aside className="run-card" id="automation">
          <span>Market call</span>
          <strong style={{ color: directionTone.color }}>
            <DirectionIcon size={26} />
            {data.consensus.consensus_score}
          </strong>
          <p>共識分數 / {data.episodes_analyzed} 集有效樣本</p>
          <small>每日台北 10:30 掃描；首頁只顯示最近兩天內的有效資料。</small>
        </aside>
      </section>

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
                    <p>{signal.thesis || signal.catalysts.slice(0, 2).join(' / ') || '等待 thesis 寫入。'}</p>
                  </div>
                  <i style={{ color: tone.color }}>{tone.label}</i>
                  <em>{signal.confidence_score}</em>
                  <small>{signal.source_count} KOL</small>
                </Link>
              )
            }) : (
              <p className="empty-note">尚無最近兩天內的訊號。Podcast scanner 寫入 daily_signals 後會出現在這裡。</p>
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
              <strong>{bearishSignal ? bearishSignal.ticker : 'None'}</strong>
              <p>{bearishSignal ? bearishSignal.thesis || `${bearishSignal.source_count} 位 KOL 偏空。` : '目前未偵測到高信心偏空訊號。'}</p>
            </div>
            <div>
              <span>擁擠標的</span>
              <strong>{crowdedStock ? crowdedStock.ticker : 'None'}</strong>
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
      <div className="insight-pill">核心觀點</div>
      <p>{episode.summary.replace(/\s+/g, ' ').trim() || '尚無摘要內容'}</p>
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
