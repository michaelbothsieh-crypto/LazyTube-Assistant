import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getAllKolIds, getEpisodeByKolId, getLatestStocks, getConsensusHistory } from '@/lib/data'
import ConsensusChart from '@/components/ConsensusChart'
import { ArrowLeft, TrendUp, TrendDown, Minus, ExternalLink } from '@/components/icons'

export const revalidate = 300

export async function generateStaticParams() {
  const ids = await getAllKolIds()
  return ids.map(kol_id => ({ kol_id }))
}

const SENT = {
  bullish: { label: '多方看好', color: 'var(--bullish)', bg: 'var(--bullish-bg)', border: 'var(--bullish-border)', Icon: TrendUp },
  bearish: { label: '空方謹慎', color: 'var(--bearish)', bg: 'var(--bearish-bg)', border: 'var(--bearish-border)', Icon: TrendDown },
  neutral: { label: '中性觀望', color: 'var(--neutral)', bg: 'var(--neutral-bg)', border: 'var(--neutral-border)', Icon: Minus },
}

export default async function KOLDetailPage({ params }: { params: Promise<{ kol_id: string }> }) {
  const { kol_id } = await params

  const [ep, latestStocks, history] = await Promise.all([
    getEpisodeByKolId(kol_id),
    getLatestStocks(),
    getConsensusHistory(),
  ])

  if (!ep) notFound()

  const sc = SENT[ep.sentiment]
  const accentColor = ep.color || '#81ffd4'

  const stockDetails = ep.stocks_mentioned.map(ticker => {
    const found = latestStocks.find(s => s.ticker === ticker)
    return found ?? { ticker, name: ticker, market: 'US' as const, mentions: 1, sentiment: 'neutral' as const, kols: [] }
  })

  // Double for seamless CSS marquee loop
  const marqueeTickers = stockDetails.length > 0
    ? [...stockDetails, ...stockDetails]
    : []

  return (
    <div className="kol-detail-root">

      {/* Floating pill nav — mirrors homepage .taste-nav */}
      <nav className="taste-nav">
        <Link href="/" className="kol-back-link">
          <ArrowLeft size={15} />
          儀表板
        </Link>
        <span className="taste-brand" style={{ maxWidth: '40%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {ep.kol_name}
        </span>
        <span className="taste-chip">{ep.published}</span>
      </nav>

      {/* Hero — editorial dark aesthetic matching homepage */}
      <section className="kol-hero chapter">
        <div
          className="kol-hero-backdrop"
          style={{
            background: `radial-gradient(70% 70% at 50% 0%, ${accentColor}28 0%, transparent 70%)`,
          }}
        />
        <div
          className="kol-hero-avatar"
          style={{ background: `${accentColor}18`, border: `2px solid ${accentColor}40`, color: accentColor }}
        >
          {ep.avatar || ep.kol_name[0] || '?'}
        </div>
        <p className="hero-kicker">{ep.host} · Podcast</p>
        <h1 className="hero-title kol-hero-title">
          {ep.title}
        </h1>
        <div className="kol-hero-badges">
          <span
            className="kol-sentiment-badge"
            style={{ background: sc.bg, border: `1px solid ${sc.border}`, color: sc.color }}
          >
            <sc.Icon size={14} />
            {sc.label}
          </span>
          {ep.report_url && (
            <a
              href={ep.report_url}
              target="_blank"
              rel="noopener noreferrer"
              className="hero-btn hero-btn-ghost kol-report-btn"
            >
              <ExternalLink size={14} />
              AI 分析報告
            </a>
          )}
        </div>
      </section>

      {/* CSS marquee — server-component safe (no GSAP) */}
      {marqueeTickers.length > 0 && (
        <div className="taste-marquee">
          <div className="css-marquee-track">
            {marqueeTickers.map((s, i) => (
              <span key={`${s.ticker}-${i}`} className="marquee-item">
                {s.ticker} {s.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Bento grid — same 6-col system as homepage */}
      <section className="chapter-wide">
        <div className="bento-grid grid-flow-dense">

          {/* Summary — span 4：完整報告，支援換行段落 */}
          <article className="bento-card kol-summary-card">
            <p>本集完整分析</p>
            <div className="kol-summary-body">
              {ep.summary.split('\n').map((line, i) => {
                if (!line.trim()) return <div key={i} className="kol-summary-spacer" />
                if (line.startsWith('【') && line.endsWith('】'))
                  return <p key={i} className="kol-summary-section-title">{line}</p>
                return <p key={i} className="kol-summary-text">{line}</p>
              })}
            </div>
          </article>

          {/* Sentiment / meta — span 2 */}
          <article className="bento-card kol-meta-card">
            <p>情緒 / 基本資訊</p>
            <div className="kol-meta-content">
              <div className="kol-sentiment-large" style={{ color: sc.color }}>
                <sc.Icon size={28} />
                <span>{sc.label}</span>
              </div>
              <div className="kol-meta-list">
                <div className="kol-meta-row">
                  <span>主持人</span>
                  <span>{ep.host}</span>
                </div>
                <div className="kol-meta-row">
                  <span>發布日期</span>
                  <span style={{ fontFamily: 'monospace' }}>{ep.published}</span>
                </div>
                <div className="kol-meta-row">
                  <span>提及標的</span>
                  <span>{ep.stocks_mentioned.length} 檔</span>
                </div>
              </div>
            </div>
          </article>

          {/* Stocks — span 6 */}
          {stockDetails.length > 0 && (
            <article className="bento-card kol-stocks-card">
              <p>本集提及標的</p>
              <div className="kol-stocks-grid">
                {stockDetails.map(s => {
                  const ssc = SENT[s.sentiment]
                  return (
                    <div key={s.ticker} className="kol-stock-item">
                      <span className={/^\d/.test(s.ticker) ? 'ticker-tw' : 'ticker-us'}>
                        {s.ticker}
                      </span>
                      <span className="kol-stock-name">{s.name}</span>
                      <span
                        className="kol-stock-badge"
                        style={{ background: ssc.bg, border: `1px solid ${ssc.border}`, color: ssc.color }}
                      >
                        <ssc.Icon size={11} />
                        {s.sentiment === 'bullish' ? '多' : s.sentiment === 'bearish' ? '空' : '中'}
                      </span>
                      <span className="kol-stock-mentions">{s.mentions}x</span>
                    </div>
                  )
                })}
              </div>
            </article>
          )}

          {/* Chart — span 6 */}
          {history.length > 1 && (
            <article className="bento-card kol-chart-card">
              <p>共識分數歷史</p>
              <ConsensusChart history={history} />
            </article>
          )}

        </div>

        {/* Footer — mirrors .taste-footer */}
        <div className="taste-footer" style={{ marginTop: '4rem' }}>
          <Link href="/" className="kol-back-link">
            <ArrowLeft size={14} />
            回到所有 KOL 今日摘要
          </Link>
          <span>PodConsensus</span>
          <span>{ep.published}</span>
        </div>
      </section>

    </div>
  )
}
