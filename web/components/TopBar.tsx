'use client'
import { Activity, Clock } from '@/components/icons'

export default function TopBar({
  date, generatedAt, episodesCount
}: { date: string; generatedAt: string; episodesCount: number }) {
  const time = generatedAt
    ? new Date(generatedAt).toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })
    : ''

  return (
    <header
      className="sticky top-0 z-50"
      style={{
        background: 'rgba(255,255,255,0.92)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">

        {/* Brand */}
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-black"
            style={{
              background: 'var(--accent)',
              color: '#fff',
            }}
          >
            PC
          </div>
          <span className="font-bold text-[var(--text-1)] tracking-tight text-sm sm:text-base">
            PodConsensus
          </span>
          <span
            className="hidden sm:block text-[11px] section-label border rounded px-2 py-0.5"
            style={{ borderColor: 'var(--border)', color: 'var(--text-4)' }}
          >
            財經 KOL 共識儀表板
          </span>
        </div>

        {/* Right status */}
        <div className="flex items-center gap-4">
          <span className="hidden sm:flex items-center gap-1.5 text-sm text-[var(--text-3)]">
            <Activity size={14} style={{ color: 'var(--accent)' }} />
            {episodesCount} 集已分析
          </span>

          <span className="hidden md:flex items-center gap-1.5 text-xs font-mono text-[var(--text-4)]">
            <Clock size={13} />
            {date}{time && ` · ${time}`}
          </span>

          <span className="flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full live-dot inline-block"
              style={{ background: 'var(--bullish)' }}
            />
            <span className="text-xs font-semibold" style={{ color: 'var(--bullish)' }}>LIVE</span>
          </span>
        </div>

      </div>
    </header>
  )
}
