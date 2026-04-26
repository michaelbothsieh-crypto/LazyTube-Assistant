import Link from 'next/link'
import type { Episode } from '@/types'
import { Mic, TrendUp, TrendDown, Minus, ChevronRight, Calendar, Users, ExternalLink } from '@/components/icons'

const SENTIMENT = {
  bullish: { label: '多方看好', cls: 'pill-bullish', color: 'var(--bullish)', Icon: TrendUp },
  bearish: { label: '空方謹慎', cls: 'pill-bearish', color: 'var(--bearish)', Icon: TrendDown },
  neutral: { label: '中性觀望', cls: 'pill-neutral', color: 'var(--neutral)', Icon: Minus },
}

/* Large featured card — horizontal layout */
function FeaturedCard({ ep }: { ep: Episode }) {
  const sc = SENTIMENT[ep.sentiment]

  return (
    <Link href={`/kol/${ep.kol_id}`} className="block group">
      <div
        className="card overflow-hidden transition-all duration-200 group-hover:-translate-y-0.5"
        style={{ borderLeft: `4px solid ${ep.color}` }}
      >
        <div className="flex flex-col sm:flex-row">
          {/* Sidebar: avatar + name */}
          <div
            className="sm:w-52 flex-shrink-0 p-6 flex flex-col gap-3"
            style={{ background: 'var(--surface-2)', borderRight: '1px solid var(--border)' }}
          >
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-black"
              style={{ background: `${ep.color}20`, border: `2px solid ${ep.color}40`, color: ep.color }}
            >
              {ep.kol_name[0]}
            </div>
            <div>
              <p className="text-base font-bold text-[var(--text-1)]">{ep.kol_name}</p>
              <div className="flex items-center gap-1 mt-1 text-xs text-[var(--text-3)]">
                <Users size={12} />
                <span>{ep.host}</span>
              </div>
              <div className="flex items-center gap-1 mt-1 text-xs text-[var(--text-4)] font-mono">
                <Calendar size={12} />
                <span>{ep.published}</span>
              </div>
            </div>
            <span
              className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full mt-auto ${sc.cls}`}
            >
              <sc.Icon size={13} />
              {sc.label}
            </span>
          </div>

          {/* Main content */}
          <div className="flex-1 p-6 flex flex-col gap-4">
            {/* Podcast label */}
            <div className="flex items-center gap-2">
              <Mic size={14} style={{ color: 'var(--text-4)' }} />
              <span className="section-label">Podcast 摘要</span>
            </div>

            <div className="flex-1">
              <h3 className="text-lg font-bold text-[var(--text-1)] leading-snug mb-3">
                {ep.title}
              </h3>
              <p className="text-sm text-[var(--text-2)] leading-relaxed line-clamp-3 max-w-[65ch]">
                {ep.summary}
              </p>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
              <div className="flex flex-wrap gap-1.5">
                {ep.stocks_mentioned.slice(0, 5).map(t => (
                  <span key={t} className={/^\d/.test(t) ? 'ticker-tw' : 'ticker-us'}>{t}</span>
                ))}
              </div>
              <span
                className="inline-flex items-center gap-1.5 text-sm font-semibold transition-colors group-hover:text-[var(--accent)]"
                style={{ color: 'var(--text-3)' }}
              >
                查看完整報告
                <ChevronRight size={16} className="transition-transform duration-150 group-hover:translate-x-0.5" />
              </span>
            </div>
          </div>
        </div>
      </div>
    </Link>
  )
}

/* Compact card — vertical, for grid */
function CompactCard({ ep, index }: { ep: Episode; index: number }) {
  const sc = SENTIMENT[ep.sentiment]

  return (
    <Link href={`/kol/${ep.kol_id}`} className="block group fade-up" style={{ animationDelay: `${index * 0.05}s` }}>
      <div
        className="card overflow-hidden h-full flex flex-col transition-all duration-200 group-hover:-translate-y-0.5"
        style={{ borderTop: `3px solid ${ep.color}` }}
      >
        <div className="p-5 flex flex-col gap-4 flex-1">
          {/* Header */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold flex-shrink-0"
                style={{ background: `${ep.color}18`, border: `1.5px solid ${ep.color}40`, color: ep.color }}
              >
                {ep.kol_name[0]}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-bold text-[var(--text-1)] truncate">{ep.kol_name}</p>
                <p className="text-xs text-[var(--text-4)] truncate">{ep.host}</p>
              </div>
            </div>
            <span
              className={`inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-full flex-shrink-0 ${sc.cls}`}
            >
              <sc.Icon size={11} />
              {ep.sentiment === 'bullish' ? '多' : ep.sentiment === 'bearish' ? '空' : '中'}
            </span>
          </div>

          {/* Title */}
          <div className="flex-1">
            <p className="text-sm font-bold text-[var(--text-1)] line-clamp-2 leading-snug mb-2">
              {ep.title}
            </p>
            <p className="text-xs text-[var(--text-3)] line-clamp-3 leading-relaxed">
              {ep.summary}
            </p>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between pt-3 border-t" style={{ borderColor: 'var(--border)' }}>
            <div className="flex flex-wrap gap-1.5">
              {ep.stocks_mentioned.slice(0, 3).map(t => (
                <span key={t} className={/^\d/.test(t) ? 'ticker-tw' : 'ticker-us'}>{t}</span>
              ))}
            </div>
            <div className="flex items-center gap-1 text-[11px] font-mono text-[var(--text-4)]">
              <Calendar size={11} />
              {ep.published}
            </div>
          </div>
        </div>

        {/* Bottom action bar */}
        <div
          className="px-5 py-3 flex items-center justify-end gap-1.5 text-xs font-semibold transition-colors"
          style={{
            background: 'var(--surface-2)',
            borderTop: '1px solid var(--border)',
            color: 'var(--text-4)',
          }}
        >
          <ExternalLink size={12} />
          查看詳情
          <ChevronRight size={12} className="transition-transform duration-150 group-hover:translate-x-0.5" />
        </div>
      </div>
    </Link>
  )
}

export default function KOLGrid({ episodes }: { episodes: Episode[] }) {
  if (!episodes.length) return null
  const [featured, ...rest] = episodes

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="section-label mb-1">今日更新頻道</p>
          <div className="flex items-center gap-2">
            <Mic size={18} style={{ color: 'var(--accent)' }} />
            <h2 className="text-base font-bold text-[var(--text-1)]">KOL 播客分析摘要</h2>
          </div>
        </div>
        <span className="text-xs font-mono text-[var(--text-4)]">{episodes.length} 集</span>
      </div>

      {/* Featured card */}
      <FeaturedCard ep={featured} />

      {/* 2-col grid for rest */}
      {rest.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {rest.map((ep, i) => (
            <CompactCard key={`${ep.kol_id}-${i}`} ep={ep} index={i} />
          ))}
        </div>
      )}
    </section>
  )
}
