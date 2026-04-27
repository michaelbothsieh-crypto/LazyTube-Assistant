'use client'

import { useRef } from 'react'
import { useState } from 'react'
import Link from 'next/link'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import type { ConsensusData } from '@/types'

gsap.registerPlugin(ScrollTrigger)

type TasteLandingProps = {
  data: ConsensusData
}

const sentimentColor = {
  bullish: '#5af0b0',
  neutral: '#97a6be',
  bearish: '#ff8f8f',
} as const

const copy = {
  zh: {
    navInsight: '洞察',
    navSignals: '訊號',
    navAction: '行動',
    kicker: '每日聲音情報，重組成可執行市場觀點',
    title: '台美股 Podcast 共識儀表板',
    sub: '把每日多位財經 KOL 的內容壓縮成單一市場視角：熱門標的、情緒傾向、跨頻道共識，一頁完成。',
    cta1: '查看今日共識',
    cta2: '前往行動區',
    score: '共識分數',
    generatedAt: '更新時間',
    thesis: '本週主軸',
    sentiment: '市場情緒',
    bullish: '偏多',
    neutral: '中性',
    bearish: '偏空',
    topStocks: '高共識標的',
    vectors: '討論向量',
    desireTitle: '共識正在集中的地方',
    reveal:
      '這不是單純的提及次數統計，而是跨節目重複驗證後的市場傾向。你可以從中快速判斷資金偏好、節奏變化與風險切換訊號。',
    actionTitle: '在下一個開盤前，先把共識轉成策略',
    actionBody:
      '把分散的 Podcast 筆記，收斂成同一張決策畫布。你可以更快判斷部位節奏、風險曝險與跨頻道觀點重疊度。',
    actionCta1: '重新掃描共識',
    actionCta2: '檢視 KOL 集數',
    episodes: '集數',
  },
  en: {
    navInsight: 'Insight',
    navSignals: 'Signals',
    navAction: 'Action',
    kicker: 'Audio market intelligence, restructured into conviction',
    title: 'Daily Podcast Consensus for Taiwan and US Equities',
    sub: 'Compress multiple financial podcast voices into one decision surface: high-conviction names, sentiment tilt, and cross-channel alignment.',
    cta1: 'Explore consensus',
    cta2: 'Jump to action',
    score: 'Consensus score',
    generatedAt: 'Generated at',
    thesis: 'Weekly thesis',
    sentiment: 'Market sentiment',
    bullish: 'Bullish',
    neutral: 'Neutral',
    bearish: 'Bearish',
    topStocks: 'Highest agreement names',
    vectors: 'Conversation vectors',
    desireTitle: 'Where consensus concentrates',
    reveal:
      'This is not just mention counting. It captures repeated confirmation across hosts so you can identify capital preference, momentum shifts, and risk-transfer signals faster.',
    actionTitle: 'Deploy this signal stack before the next open',
    actionBody:
      'Move from fragmented podcast notes to one operating canvas. Decide position rhythm, risk exposure, and cross-host overlap with less noise.',
    actionCta1: 'Re-run the consensus lens',
    actionCta2: 'Review analyst episodes',
    episodes: 'episodes',
  },
} as const

export default function TasteLanding({ data }: TasteLandingProps) {
  const rootRef = useRef<HTMLElement | null>(null)
  const textRevealRef = useRef<HTMLParagraphElement | null>(null)
  const [locale, setLocale] = useState<'zh' | 'en'>('zh')
  const t = copy[locale]

  useGSAP(
    () => {
      const images = gsap.utils.toArray<HTMLElement>('[data-scale-image]')
      images.forEach((el) => {
        gsap.fromTo(
          el,
          { scale: 0.82, opacity: 0.25, filter: 'grayscale(75%) brightness(0.55)' },
          {
            scale: 1,
            opacity: 1,
            filter: 'grayscale(0%) brightness(1)',
            ease: 'none',
            scrollTrigger: {
              trigger: el,
              start: 'top 78%',
              end: 'bottom 25%',
              scrub: true,
            },
          }
        )
      })

      if (textRevealRef.current) {
        const words = textRevealRef.current.querySelectorAll('span')
        gsap.set(words, { opacity: 0.12 })
        gsap.to(words, {
          opacity: 1,
          ease: 'none',
          stagger: 0.14,
          scrollTrigger: {
            trigger: textRevealRef.current,
            start: 'top 80%',
            end: 'bottom 20%',
            scrub: true,
          },
        })
      }

      const marquee = gsap.utils.toArray<HTMLElement>('[data-marquee-track]')
      marquee.forEach((track) => {
        const width = track.scrollWidth / 2
        gsap.to(track, {
          x: -width,
          ease: 'none',
          duration: 26,
          repeat: -1,
        })
      })
    },
    { scope: rootRef }
  )

  const [sentFilter, setSentFilter] = useState<'all' | 'bullish' | 'neutral' | 'bearish'>('all')

  const topStocks = data.consensus.stocks.slice(0, 5)
  const keywords = data.consensus.top_keywords.slice(0, 5)
  const episodes = data.episodes.slice(0, 15)

  const filteredEpisodes = sentFilter === 'all' ? episodes : episodes.filter(ep => ep.sentiment === sentFilter)
  const bullishCount = episodes.filter(ep => ep.sentiment === 'bullish').length
  const neutralCount = episodes.filter(ep => ep.sentiment === 'neutral').length
  const bearishCount = episodes.filter(ep => ep.sentiment === 'bearish').length

  return (
    <main ref={rootRef} className="taste-root overflow-x-hidden w-full max-w-full">
      <nav className="taste-nav">
        <span className="taste-brand">PodConsensus</span>
        <div className="taste-links">
          <a href="#insight">{t.navInsight}</a>
          <a href="#desire">{t.navSignals}</a>
          <a href="#action">{t.navAction}</a>
        </div>
        <div className="taste-lang-toggle" role="group" aria-label="Language switcher">
          <button
            type="button"
            onClick={() => setLocale('zh')}
            className={locale === 'zh' ? 'is-active' : ''}
          >
            中文
          </button>
          <button
            type="button"
            onClick={() => setLocale('en')}
            className={locale === 'en' ? 'is-active' : ''}
          >
            EN
          </button>
        </div>
        <span className="taste-chip">{data.date}</span>
      </nav>

      <section className="taste-hero chapter">
        <div className="hero-backdrop" />
        <p className="hero-kicker">{t.kicker}</p>
        <h1 className="hero-title max-w-6xl">
          {t.title}
          <span
            className="hero-inline-image"
            style={{ backgroundImage: 'url(https://picsum.photos/seed/market-velocity/320/140)' }}
          />
        </h1>
        <p className="hero-sub max-w-3xl">
          {t.sub}
        </p>
        <div className="hero-cta-row">
          <a className="hero-btn hero-btn-primary" href="#insight">
            {t.cta1}
          </a>
          <a className="hero-btn hero-btn-ghost" href="#action">
            {t.cta2}
          </a>
        </div>
      </section>

      <section id="insight" className="chapter chapter-wide">
        <div className="taste-marquee">
          <div data-marquee-track className="marquee-track">
            {[...topStocks, ...topStocks].map((stock, i) => (
              <span key={`${stock.ticker}-${i}`} className="marquee-item">
                {stock.ticker} {stock.name}
              </span>
            ))}
          </div>
        </div>

        <div className="bento-grid grid-flow-dense">
          <article className="bento-card bento-score">
            <p>{t.score}</p>
            <strong>{data.consensus.consensus_score}</strong>
            <small>{t.generatedAt} {data.generated_at}</small>
          </article>

          <article className="bento-card bento-theme">
            <div className="bento-theme-glow" />
            <div>
              <p>{t.thesis}</p>
              <h3>{data.consensus.weekly_theme}</h3>
            </div>
          </article>

          <article className="bento-card bento-sentiment">
            <p>{t.sentiment}</p>
            <ul>
              <li>
                <span>{t.bullish}</span>
                <strong>{data.consensus.market_sentiment.bullish}%</strong>
              </li>
              <li>
                <span>{t.neutral}</span>
                <strong>{data.consensus.market_sentiment.neutral}%</strong>
              </li>
              <li>
                <span>{t.bearish}</span>
                <strong>{data.consensus.market_sentiment.bearish}%</strong>
              </li>
            </ul>
          </article>

          <article className="bento-card bento-stocks">
            <p>{t.topStocks}</p>
            <ul>
              {topStocks.map((stock) => (
                <li key={stock.ticker}>
                  <span>{stock.ticker}</span>
                  <small>{stock.name}</small>
                  <strong style={{ color: sentimentColor[stock.sentiment] }}>{stock.mentions}x</strong>
                </li>
              ))}
            </ul>
          </article>

          <article className="bento-card bento-keywords">
            <p>{t.vectors}</p>
            <div>
              {keywords.map((word) => (
                <span key={word}>{word}</span>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section id="desire" className="chapter chapter-wide">
        <div className="kol-section-header">
          <h2>{t.desireTitle}</h2>
          <div className="kol-filter-tabs">
            <button
              type="button"
              className={sentFilter === 'all' ? 'active' : ''}
              onClick={() => setSentFilter('all')}
            >
              全部 {episodes.length}
            </button>
            <button
              type="button"
              className={sentFilter === 'bullish' ? 'active' : ''}
              onClick={() => setSentFilter('bullish')}
            >
              多方 {bullishCount}
            </button>
            <button
              type="button"
              className={sentFilter === 'neutral' ? 'active-neutral' : ''}
              onClick={() => setSentFilter('neutral')}
            >
              中性 {neutralCount}
            </button>
            {bearishCount > 0 && (
              <button
                type="button"
                className={sentFilter === 'bearish' ? 'active-bearish' : ''}
                onClick={() => setSentFilter('bearish')}
              >
                空方 {bearishCount}
              </button>
            )}
          </div>
        </div>

        <div className="kol-grid">
          {filteredEpisodes.map((ep, i) => {
            const sentLabel = ep.sentiment === 'bullish' ? t.bullish : ep.sentiment === 'bearish' ? t.bearish : t.neutral
            const sentBg = ep.sentiment === 'bullish'
              ? 'rgba(129,255,212,0.12)'
              : ep.sentiment === 'bearish'
              ? 'rgba(255,143,143,0.12)'
              : 'rgba(151,166,190,0.12)'
            const sentBorder = ep.sentiment === 'bullish'
              ? 'rgba(129,255,212,0.3)'
              : ep.sentiment === 'bearish'
              ? 'rgba(255,143,143,0.3)'
              : 'rgba(151,166,190,0.3)'
            return (
              <Link key={`${ep.kol_id}-${i}`} href={`/kol/${ep.kol_id}`} className="kol-card">
                <div className="kol-card-top">
                  <div className="kol-card-avatar">{ep.avatar || ep.kol_name[0] || '🎙'}</div>
                  <span className="kol-card-name">{ep.kol_name}</span>
                  <span
                    className="kol-card-sent"
                    style={{ background: sentBg, border: `1px solid ${sentBorder}`, color: sentimentColor[ep.sentiment] }}
                  >
                    {sentLabel}
                  </span>
                </div>
                <p className="kol-card-title">{ep.title}</p>
                <div className="kol-card-tickers">
                  {ep.stocks_mentioned.slice(0, 5).map(ticker => (
                    <span key={ticker}>{ticker}</span>
                  ))}
                </div>
              </Link>
            )
          })}
        </div>
      </section>

      <section id="action" className="chapter chapter-wide action-section">
        <h2>{t.actionTitle}</h2>
        <p>{t.actionBody}</p>
        <div className="hero-cta-row">
          <a className="hero-btn hero-btn-primary" href="#insight">
            {t.actionCta1}
          </a>
          <a className="hero-btn hero-btn-ghost" href="#desire">
            {t.actionCta2}
          </a>
        </div>
        <footer className="taste-footer">
          <span>PodConsensus</span>
          <span>{data.date}</span>
          <span>{data.episodes_analyzed} {t.episodes}</span>
        </footer>
      </section>
    </main>
  )
}
