import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getAllKolIds, getConsensusHistory, getEpisodeByKolId, getLatestStocks } from '@/lib/data'
import ConsensusChart from '@/components/ConsensusChart'
import { ArrowLeft, BarChart2, ExternalLink, Minus, TrendDown, TrendUp } from '@/components/icons'

export const dynamicParams = true
export const revalidate = 300

export async function generateStaticParams() {
  const ids = await getAllKolIds()
  return ids.map((kol_id) => ({ kol_id }))
}

const sentiment = {
  bullish: { label: '偏多', color: 'var(--gain)', Icon: TrendUp },
  bearish: { label: '偏空', color: 'var(--risk)', Icon: TrendDown },
  neutral: { label: '中性', color: 'var(--muted)', Icon: Minus },
} as const

const ignoredTickers = new Set(['GEO', 'CNC', 'RFID', 'HID', 'ASSA', 'ABLOY', 'NFC'])

function splitSummary(summary: string, limit = 18) {
  return summary
    .replace(/\r/g, '\n')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, limit)
}

export default async function KOLDetailPage({ params }: { params: Promise<{ kol_id: string }> }) {
  const { kol_id } = await params

  const [episode, latestStocks, history] = await Promise.all([
    getEpisodeByKolId(kol_id),
    getLatestStocks(),
    getConsensusHistory(),
  ])

  if (!episode) notFound()

  const tone = sentiment[episode.sentiment]
  const ToneIcon = tone.Icon
  const stockMap = new Map(latestStocks.map((stock) => [stock.ticker, stock]))
  const stockDetails = episode.stocks_mentioned.filter((ticker) => !ignoredTickers.has(ticker)).map((ticker) => (
    stockMap.get(ticker) ?? {
      ticker,
      name: ticker,
      market: /^\d/.test(ticker) ? 'TW' as const : 'US' as const,
      mentions: 1,
      sentiment: 'neutral' as const,
      kols: [],
    }
  ))
  const summaryLines = splitSummary(episode.investment_note || episode.summary)
  const transcriptLines = splitSummary(episode.transcript, 80)

  return (
    <main className="detail-shell overflow-x-hidden w-full max-w-full">
      <nav className="research-nav detail-report-nav" aria-label="Detail navigation">
        <Link href="/" className="brand-mark detail-back">
          <ArrowLeft size={16} />
          回首頁
        </Link>
        <div>
          <span>{episode.kol_name}</span>
          <span>{episode.published}</span>
        </div>
      </nav>

      <section className="detail-report-header">
        <div className="detail-report-title">
          <p className="eyebrow">KOL episode research note</p>
          <h1>{episode.title}</h1>
          <div className="detail-hero-meta">
            <span style={{ color: tone.color }}>
              <ToneIcon size={16} />
              {tone.label}
            </span>
            <span>{episode.host || 'Podcast host'}</span>
            <span>{stockDetails.length || '主題型'} 標的</span>
          </div>
          {episode.report_url && (
            <a className="btn btn-secondary detail-report" href={episode.report_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink size={16} />
              開啟報告
            </a>
          )}
        </div>

        <aside className="detail-kol-card">
          <span className="card-label">KOL profile</span>
          <div className="host-avatar" style={{ color: episode.color, borderColor: `${episode.color}55`, background: `${episode.color}18` }}>
            {episode.avatar || episode.kol_name.slice(0, 1)}
          </div>
          <h2>{episode.kol_name}</h2>
          <dl>
            <div>
              <dt>主持人</dt>
              <dd>{episode.host || '-'}</dd>
            </div>
            <div>
              <dt>發布日期</dt>
              <dd>{episode.published}</dd>
            </div>
            <div>
              <dt>方向</dt>
              <dd style={{ color: tone.color }}>{tone.label}</dd>
            </div>
          </dl>
        </aside>
      </section>

      <section className="detail-grid-section compact-detail-grid">
        <div className="detail-bento">
          <article className="detail-summary-card">
            <span className="card-label">投資小結</span>
            <div className="summary-flow">
              {(summaryLines.length ? summaryLines : [episode.summary || '尚無摘要內容']).map((line, index) => (
                <p key={`${line}-${index}`}>{line}</p>
              ))}
            </div>
          </article>

          {transcriptLines.length > 0 && (
            <article className="detail-transcript-card">
              <div className="detail-card-head">
                <span className="card-label">文字紀錄</span>
                <small>{transcriptLines.length} lines</small>
              </div>
              <div className="transcript-flow">
                {transcriptLines.map((line, index) => (
                  <p key={`${line}-${index}`}>{line}</p>
                ))}
              </div>
            </article>
          )}

          <article className="detail-stock-card">
            <div className="detail-card-head">
              <span className="card-label">提及標的</span>
              <small>{stockDetails.length} names</small>
            </div>
            <div className="detail-stock-grid">
              {stockDetails.map((stock) => {
                const stockTone = sentiment[stock.sentiment]
                const StockIcon = stockTone.Icon
                return (
                  <div key={stock.ticker} className="detail-stock-item">
                    <span className={stock.market === 'TW' ? 'ticker-tw' : 'ticker-us'}>{stock.ticker}</span>
                    <strong>{stock.name}</strong>
                    <small>{stock.mentions} mentions</small>
                    <i style={{ color: stockTone.color }}>
                      <StockIcon size={13} />
                      {stockTone.label}
                    </i>
                  </div>
                )
              })}
            </div>
          </article>

          {history.length > 1 && (
            <article className="detail-chart-card">
              <div className="detail-card-head">
                <span className="card-label">共識分數走勢</span>
                <BarChart2 size={18} />
              </div>
              <ConsensusChart history={history} />
            </article>
          )}
        </div>
      </section>

      <section className="detail-action compact-detail-action">
        <h2>回到每日市場研究報告</h2>
        <p>首頁會把所有 KOL 節目整理成可追蹤訊號、提及排行與資料更新狀態。</p>
        <Link href="/" className="btn btn-primary">
          <ArrowLeft size={16} />
          回到首頁
        </Link>
      </section>
    </main>
  )
}
