import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getLatestData, getEpisodeByKolId } from '@/lib/data'
import {
  ArrowLeft, Calendar, TrendUp, TrendDown, Minus,
  Mic, ExternalLink, Users, BarChart2, ChevronRight,
} from '@/components/icons'

export const revalidate = 1800

export function generateStaticParams() {
  const data = getLatestData()
  return data.episodes.map(ep => ({ kol_id: ep.kol_id }))
}

const SENT = {
  bullish: { label: '多方看好', color: 'var(--bullish)', bg: 'var(--bullish-bg)', border: 'var(--bullish-border)', Icon: TrendUp },
  bearish: { label: '空方謹慎', color: 'var(--bearish)', bg: 'var(--bearish-bg)', border: 'var(--bearish-border)', Icon: TrendDown },
  neutral: { label: '中性觀望', color: 'var(--neutral)', bg: 'var(--neutral-bg)', border: 'var(--neutral-border)', Icon: Minus },
}

export default function KOLDetailPage({ params }: { params: { kol_id: string } }) {
  const data = getLatestData()
  const ep   = getEpisodeByKolId(data, params.kol_id)
  if (!ep) notFound()

  const sc = SENT[ep.sentiment]

  const stockDetails = ep.stocks_mentioned.map(ticker => {
    const found = data.consensus.stocks.find(s => s.ticker === ticker)
    return found ?? { ticker, name: ticker, market: 'US' as const, mentions: 1, sentiment: 'neutral' as const, kols: [] }
  })

  const otherEpisodes = data.episodes.filter(
    e => e.kol_id === ep.kol_id && e.title !== ep.title
  )

  return (
    <div className="min-h-[100dvh]" style={{ background: 'var(--bg)' }}>

      {/* Sticky back nav */}
      <header
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(255,255,255,0.92)',
          backdropFilter: 'blur(16px)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm font-medium transition-colors group"
            style={{ color: 'var(--text-3)' }}
          >
            <ArrowLeft
              size={16}
              className="transition-transform duration-200 group-hover:-translate-x-0.5"
            />
            返回儀表板
          </Link>
          <span style={{ color: 'var(--border-strong)' }}>/</span>
          <span className="text-sm text-[var(--text-2)] truncate font-medium">{ep.kol_name}</span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6 scale-in">

        {/* KOL header card */}
        <div
          className="card overflow-hidden"
          style={{ borderTop: `4px solid ${ep.color}` }}
        >
          <div className="p-7 sm:p-8">
            <div className="flex items-start gap-5">
              {/* Avatar */}
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-black flex-shrink-0"
                style={{
                  background: `${ep.color}18`,
                  border: `2px solid ${ep.color}40`,
                  color: ep.color,
                }}
              >
                {ep.kol_name[0]}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-3 mb-2">
                  <h1 className="text-xl font-bold text-[var(--text-1)]">{ep.kol_name}</h1>
                  <span
                    className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full font-semibold"
                    style={{ background: sc.bg, border: `1px solid ${sc.border}`, color: sc.color }}
                  >
                    <sc.Icon size={13} />
                    {sc.label}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-4 text-sm text-[var(--text-3)]">
                  <span className="flex items-center gap-1.5">
                    <Users size={14} />
                    {ep.host}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Mic size={14} />
                    Podcast
                  </span>
                  <span className="flex items-center gap-1.5 font-mono text-xs">
                    <Calendar size={13} />
                    {ep.published}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Episode content */}
        <div className="card p-7 sm:p-8 space-y-5">
          <div>
            <p className="section-label mb-3">本集內容</p>
            <h2 className="text-lg font-bold text-[var(--text-1)] leading-snug mb-4">
              {ep.title}
            </h2>
            <p className="text-sm text-[var(--text-2)] leading-relaxed max-w-[65ch]">
              {ep.summary}
            </p>
          </div>

          {ep.report_url && (
            <a
              href={ep.report_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm font-semibold px-4 py-2.5 rounded-lg transition-colors"
              style={{
                background: 'var(--accent-bg)',
                border: '1px solid var(--accent-border)',
                color: 'var(--accent)',
              }}
            >
              <ExternalLink size={14} />
              查看完整 AI 分析報告
            </a>
          )}
        </div>

        {/* Stocks mentioned */}
        {stockDetails.length > 0 && (
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-5">
              <BarChart2 size={18} style={{ color: 'var(--accent)' }} />
              <p className="section-label">本集提及標的</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {stockDetails.map(s => {
                const ssc = SENT[s.sentiment]
                return (
                  <div
                    key={s.ticker}
                    className="flex items-center gap-3 p-4 rounded-xl transition-colors"
                    style={{
                      background: 'var(--surface-2)',
                      border: '1px solid var(--border)',
                    }}
                  >
                    <span className={/^\d/.test(s.ticker) ? 'ticker-tw' : 'ticker-us'}>
                      {s.ticker}
                    </span>
                    <span className="text-sm text-[var(--text-2)] flex-1 truncate font-medium">{s.name}</span>
                    <span
                      className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full font-semibold"
                      style={{ background: ssc.bg, border: `1px solid ${ssc.border}`, color: ssc.color }}
                    >
                      <ssc.Icon size={11} />
                      {s.sentiment === 'bullish' ? '多' : s.sentiment === 'bearish' ? '空' : '中'}
                    </span>
                    <span className="text-xs font-mono font-bold text-[var(--text-4)]">
                      {s.mentions}x
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Other episodes */}
        {otherEpisodes.length > 0 && (
          <div className="card p-6">
            <p className="section-label mb-4">同頻道其他集數</p>
            <div className="space-y-2">
              {otherEpisodes.map(other => (
                <Link
                  key={other.kol_id + other.title}
                  href={`/kol/${other.kol_id}`}
                  className="flex items-center gap-3 p-3 rounded-xl transition-colors group hover:bg-[var(--surface-2)]"
                  style={{ border: '1px solid var(--border)' }}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[var(--text-2)] truncate">{other.title}</p>
                    <p className="text-xs text-[var(--text-4)] font-mono mt-0.5">{other.published}</p>
                  </div>
                  <ChevronRight size={15} style={{ color: 'var(--text-4)' }} className="transition-transform duration-150 group-hover:translate-x-0.5" />
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Back CTA */}
        <div className="pt-2 pb-8">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm font-medium transition-colors"
            style={{ color: 'var(--text-3)' }}
          >
            <ArrowLeft size={15} />
            回到所有 KOL 今日摘要
          </Link>
        </div>

      </main>
    </div>
  )
}
