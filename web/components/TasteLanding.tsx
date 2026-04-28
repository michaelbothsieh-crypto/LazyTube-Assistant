'use client'

import { useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import type { ConsensusData, Episode } from '@/types'
import { Activity, BarChart2, ChevronRight, Clock, Minus, TrendDown, TrendUp, Users } from '@/components/icons'

gsap.registerPlugin(ScrollTrigger)

type TasteLandingProps = {
  data: ConsensusData
}

const sentimentTone = {
  bullish: { label: '偏多', color: 'var(--gain)', Icon: TrendUp },
  neutral: { label: '中性', color: 'var(--muted)', Icon: Minus },
  bearish: { label: '偏空', color: 'var(--risk)', Icon: TrendDown },
} as const

const copy = {
  zh: {
    navSignal: '共識',
    navEpisodes: '節目',
    navAction: '更新節奏',
    heroKicker: 'Podcast intelligence for public markets',
    heroTitleA: '把每日 Podcast 轉成',
    heroTitleB: '可執行的市場共識',
    heroBody: '網站每天讀取新的節目分析、股票提及與情緒分布，整理成一個能快速掃描台股與美股討論熱度的工作台。',
    primaryCta: '查看今日共識',
    secondaryCta: '瀏覽 KOL 訊號',
    score: '共識分數',
    episodes: '分析集數',
    update: '網站資料更新',
    sentiment: '市場情緒',
    topNames: '高共識標的',
    thesis: '今日主軸',
    keywords: '討論向量',
    pulseTitle: '訊號不是單一觀點，而是多個主持人重複提到的重疊區域。',
    pulseBody: '當相同標的、相同題材與相近情緒在不同節目中反覆出現，這個頁面把它折疊成較容易決策的市場表面。',
    episodeTitle: '最新節目訊號',
    all: '全部',
    bullish: '偏多',
    neutral: '中性',
    bearish: '偏空',
    actionTitle: '每日任務只更新網站資料',
    actionBody: '排程 scanner 的責任是寫入 Neon DB、重算共識並讓前端取得新資料；Telegram 僅保留手動任務或明確開啟時的回覆。',
    rerun: '回到共識',
    detail: '查看詳情',
  },
  en: {
    navSignal: 'Consensus',
    navEpisodes: 'Episodes',
    navAction: 'Cadence',
    heroKicker: 'Podcast intelligence for public markets',
    heroTitleA: 'Turn daily podcasts into',
    heroTitleB: 'an executable market consensus',
    heroBody: 'The site ingests episode analysis, ticker mentions, and sentiment distribution into one operating surface for Taiwan and US equities.',
    primaryCta: 'Read consensus',
    secondaryCta: 'Scan KOL signals',
    score: 'Consensus score',
    episodes: 'Episodes analyzed',
    update: 'Website data refresh',
    sentiment: 'Market sentiment',
    topNames: 'Highest agreement names',
    thesis: 'Daily thesis',
    keywords: 'Conversation vectors',
    pulseTitle: 'A signal is not one opinion. It is the overlap across multiple hosts.',
    pulseBody: 'When the same ticker, theme, and sentiment repeat across shows, this surface compresses the noise into something closer to a decision layer.',
    episodeTitle: 'Latest episode signals',
    all: 'All',
    bullish: 'Bullish',
    neutral: 'Neutral',
    bearish: 'Bearish',
    actionTitle: 'Daily jobs update the website data',
    actionBody: 'Scheduled scanners write Neon rows, recompute consensus, and refresh the web surface. Telegram stays reserved for manual tasks or explicit opt-in reporting.',
    rerun: 'Back to consensus',
    detail: 'Open detail',
  },
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

function stockImageSeed(ticker: string) {
  return `https://picsum.photos/seed/${encodeURIComponent(`market-${ticker}`)}/900/640`
}

export default function TasteLanding({ data }: TasteLandingProps) {
  const rootRef = useRef<HTMLElement | null>(null)
  const revealRef = useRef<HTMLParagraphElement | null>(null)
  const [locale, setLocale] = useState<'zh' | 'en'>('zh')
  const [filter, setFilter] = useState<'all' | 'bullish' | 'neutral' | 'bearish'>('all')
  const t = copy[locale]

  useGSAP(
    () => {
      const revealWords = revealRef.current?.querySelectorAll('span') ?? []
      if (revealWords.length) {
        gsap.set(revealWords, { opacity: 0.12, y: 10 })
        gsap.to(revealWords, {
          opacity: 1,
          y: 0,
          stagger: 0.08,
          ease: 'none',
          scrollTrigger: {
            trigger: revealRef.current,
            start: 'top 78%',
            end: 'bottom 35%',
            scrub: true,
          },
        })
      }

      gsap.utils.toArray<HTMLElement>('[data-stack-card]').forEach((card, index) => {
        gsap.fromTo(
          card,
          { y: 90, scale: 0.92, opacity: 0.35 },
          {
            y: index * -10,
            scale: 1,
            opacity: 1,
            ease: 'power2.out',
            scrollTrigger: {
              trigger: card,
              start: 'top 90%',
              end: 'top 42%',
              scrub: true,
            },
          },
        )
      })

      gsap.utils.toArray<HTMLElement>('[data-image-rise]').forEach((el) => {
        gsap.fromTo(
          el,
          { scale: 0.82, opacity: 0.35, filter: 'grayscale(90%) contrast(90%)' },
          {
            scale: 1,
            opacity: 1,
            filter: 'grayscale(20%) contrast(125%)',
            ease: 'none',
            scrollTrigger: {
              trigger: el,
              start: 'top 82%',
              end: 'bottom 18%',
              scrub: true,
            },
          },
        )
      })

      gsap.utils.toArray<HTMLElement>('[data-marquee-track]').forEach((track) => {
        const width = track.scrollWidth / 2
        gsap.to(track, {
          x: -width,
          duration: 30,
          repeat: -1,
          ease: 'none',
        })
      })
    },
    { scope: rootRef },
  )

  const topStocks = data.consensus.stocks.slice(0, 6)
  const heroStock = topStocks[0]
  const episodes = data.episodes.slice(0, 12)
  const filteredEpisodes = filter === 'all' ? episodes : episodes.filter((episode) => episode.sentiment === filter)
  const marqueeItems = topStocks.length ? [...topStocks, ...topStocks] : []

  const sentimentRows = useMemo(() => {
    const total = data.consensus.market_sentiment
    return [
      { key: 'bullish' as const, label: t.bullish, value: total.bullish },
      { key: 'neutral' as const, label: t.neutral, value: total.neutral },
      { key: 'bearish' as const, label: t.bearish, value: total.bearish },
    ]
  }, [data.consensus.market_sentiment, t])

  const revealWords = `${t.pulseTitle} ${t.pulseBody}`.split(' ')

  return (
    <main ref={rootRef} className="site-shell overflow-x-hidden w-full max-w-full">
      <nav className="site-nav" aria-label="Primary navigation">
        <Link href="/" className="brand-mark">PodConsensus</Link>
        <div className="nav-links">
          <a href="#consensus">{t.navSignal}</a>
          <a href="#episodes">{t.navEpisodes}</a>
          <a href="#cadence">{t.navAction}</a>
        </div>
        <div className="nav-actions">
          <button type="button" className={locale === 'zh' ? 'is-active' : ''} onClick={() => setLocale('zh')}>
            繁中
          </button>
          <button type="button" className={locale === 'en' ? 'is-active' : ''} onClick={() => setLocale('en')}>
            EN
          </button>
        </div>
      </nav>

      <section className="hero-editorial">
        <div className="hero-copy">
          <p className="eyebrow">{t.heroKicker}</p>
          <h1>
            {t.heroTitleA}
            <span
              className="inline-market-image"
              style={{ backgroundImage: `url(${stockImageSeed(heroStock?.ticker ?? 'consensus')})` }}
            />
            {t.heroTitleB}
          </h1>
          <p className="hero-body">{t.heroBody}</p>
          <div className="hero-actions">
            <a className="btn btn-primary" href="#consensus">{t.primaryCta}</a>
            <a className="btn btn-secondary" href="#episodes">{t.secondaryCta}</a>
          </div>
        </div>
        <div className="hero-panel" data-image-rise>
          <div className="hero-panel-image" style={{ backgroundImage: `url(${stockImageSeed(heroStock?.ticker ?? 'dashboard')})` }} />
          <div className="hero-panel-content">
            <span>{data.date}</span>
            <strong>{heroStock ? `${heroStock.ticker} ${heroStock.name}` : t.topNames}</strong>
            <p>{data.consensus.weekly_theme || t.thesis}</p>
          </div>
        </div>
      </section>

      {marqueeItems.length > 0 && (
        <div className="signal-marquee" aria-hidden="true">
          <div className="marquee-track" data-marquee-track>
            {marqueeItems.map((stock, index) => (
              <span key={`${stock.ticker}-${index}`}>
                {stock.ticker} {stock.name} {stock.mentions}x
              </span>
            ))}
          </div>
        </div>
      )}

      <section id="consensus" className="chapter-section">
        <div className="section-heading">
          <p className="eyebrow">{t.update} {formatDateTime(data.generated_at)}</p>
          <h2>{t.thesis}</h2>
        </div>
        <div className="data-bento">
          <article className="metric-card metric-score" data-stack-card>
            <div className="metric-icon"><Activity size={20} /></div>
            <span>{t.score}</span>
            <strong>{data.consensus.consensus_score}</strong>
            <p>{data.consensus.weekly_theme || '等待新的共識資料'}</p>
          </article>

          <article className="metric-card" data-stack-card>
            <div className="metric-icon"><Users size={20} /></div>
            <span>{t.episodes}</span>
            <strong>{data.episodes_analyzed}</strong>
            <p>{data.date}</p>
          </article>

          <article className="metric-card" data-stack-card>
            <div className="metric-icon"><Clock size={20} /></div>
            <span>{t.update}</span>
            <strong>300s</strong>
            <p>ISR revalidate window</p>
          </article>

          <article className="wide-card sentiment-card" data-stack-card>
            <div>
              <span className="card-label">{t.sentiment}</span>
              <h3>{data.consensus.market_sentiment.bullish >= 50 ? t.bullish : data.consensus.market_sentiment.bearish >= 50 ? t.bearish : t.neutral}</h3>
            </div>
            <div className="sentiment-bars">
              {sentimentRows.map((row) => (
                <div key={row.key}>
                  <span>{row.label}</span>
                  <div className="bar-rail">
                    <i style={{ width: `${row.value}%`, background: sentimentTone[row.key].color }} />
                  </div>
                  <strong>{row.value}%</strong>
                </div>
              ))}
            </div>
          </article>

          <article className="stock-card" data-stack-card>
            <span className="card-label">{t.topNames}</span>
            <div className="stock-list">
              {topStocks.map((stock, index) => {
                const tone = sentimentTone[stock.sentiment]
                return (
                  <Link href="#episodes" key={stock.ticker} className="stock-row">
                    <b>{String(index + 1).padStart(2, '0')}</b>
                    <span>{stock.ticker}</span>
                    <small>{stock.name}</small>
                    <strong style={{ color: tone.color }}>{stock.mentions}x</strong>
                  </Link>
                )
              })}
            </div>
          </article>

          <article className="keyword-card" data-stack-card>
            <span className="card-label">{t.keywords}</span>
            <div>
              {data.consensus.top_keywords.slice(0, 8).map((keyword) => (
                <span key={keyword}>{keyword}</span>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section className="narrative-section">
        <p ref={revealRef} className="reveal-copy">
          {revealWords.map((word, index) => (
            <span key={`${word}-${index}`}>{word} </span>
          ))}
        </p>
      </section>

      <section id="episodes" className="chapter-section episode-section">
        <div className="section-heading section-heading-row">
          <div>
            <p className="eyebrow">KOL signal board</p>
            <h2>{t.episodeTitle}</h2>
          </div>
          <div className="filter-tabs">
            {(['all', 'bullish', 'neutral', 'bearish'] as const).map((item) => (
              <button key={item} type="button" className={filter === item ? 'is-active' : ''} onClick={() => setFilter(item)}>
                {item === 'all' ? t.all : t[item]}
              </button>
            ))}
          </div>
        </div>

        <div className="episode-accordion">
          {filteredEpisodes.map((episode, index) => (
            <EpisodeSlice key={`${episode.kol_id}-${index}`} episode={episode} index={index} detailLabel={t.detail} />
          ))}
        </div>
      </section>

      <section id="cadence" className="action-band">
        <div>
          <BarChart2 size={28} />
          <h2>{t.actionTitle}</h2>
          <p>{t.actionBody}</p>
          <a className="btn btn-primary" href="#consensus">{t.rerun}</a>
        </div>
        <footer>
          <span>PodConsensus</span>
          <span>{data.date}</span>
          <span>{data.episodes_analyzed} {t.episodes}</span>
        </footer>
      </section>
    </main>
  )
}

function EpisodeSlice({ episode, index, detailLabel }: { episode: Episode; index: number; detailLabel: string }) {
  const tone = sentimentTone[episode.sentiment]
  const Icon = tone.Icon
  const image = `https://picsum.photos/seed/${encodeURIComponent(`kol-${episode.kol_id}-${index}`)}/900/700`

  return (
    <Link href={`/kol/${episode.kol_id}`} className="episode-slice group">
      <div className="episode-art" data-image-rise>
        <div style={{ backgroundImage: `url(${image})` }} />
      </div>
      <div className="episode-body">
        <div className="episode-topline">
          <span>{episode.kol_name}</span>
          <small>{episode.published}</small>
        </div>
        <h3>{episode.title}</h3>
        <p>{episode.summary}</p>
        <div className="episode-meta">
          <span style={{ color: tone.color }}>
            <Icon size={14} />
            {tone.label}
          </span>
          {episode.stocks_mentioned.slice(0, 4).map((ticker) => (
            <b key={ticker}>{ticker}</b>
          ))}
          <i>
            {detailLabel}
            <ChevronRight size={14} />
          </i>
        </div>
      </div>
    </Link>
  )
}
