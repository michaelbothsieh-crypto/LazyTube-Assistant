import { TrendUp, TrendDown, Minus } from '@/components/icons'

type Sentiment = { bullish: number; bearish: number; neutral: number }

export default function SentimentMeter({ sentiment }: { sentiment: Sentiment }) {
  const { bullish, bearish, neutral } = sentiment

  const segments = [
    { label: '多方看好', pct: bullish, color: 'var(--bullish)', bg: 'var(--bullish-bg)', border: 'var(--bullish-border)', Icon: TrendUp },
    { label: '中性觀望', pct: neutral, color: 'var(--neutral)', bg: 'var(--neutral-bg)', border: 'var(--neutral-border)', Icon: Minus },
    { label: '空方謹慎', pct: bearish, color: 'var(--bearish)', bg: 'var(--bearish-bg)', border: 'var(--bearish-border)', Icon: TrendDown },
  ] as const

  const dominant = bullish >= bearish && bullish >= neutral ? segments[0]
    : bearish >= bullish && bearish >= neutral ? segments[2]
    : segments[1]

  return (
    <div className="card p-6 flex flex-col gap-5">
      <div>
        <p className="section-label mb-1">市場情緒分布</p>
        <div className="flex items-center gap-2 mt-2">
          <dominant.Icon size={18} style={{ color: dominant.color }} />
          <p className="text-base font-bold text-[var(--text-1)]">{dominant.label}</p>
        </div>
      </div>

      {/* Stacked bar */}
      <div className="h-3 rounded-full overflow-hidden flex" style={{ background: 'var(--border)' }}>
        <div style={{ width: `${bullish}%`, background: 'var(--bullish)', transition: 'width 0.8s ease' }} />
        <div style={{ width: `${neutral}%`, background: '#cbd5e1', transition: 'width 0.8s ease' }} />
        <div style={{ width: `${bearish}%`, background: 'var(--bearish)', transition: 'width 0.8s ease' }} />
      </div>

      {/* Stat rows */}
      <div className="space-y-3">
        {segments.map(seg => (
          <div key={seg.label} className="flex items-center gap-3">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ background: seg.bg, border: `1px solid ${seg.border}` }}
            >
              <seg.Icon size={16} style={{ color: seg.color }} />
            </div>
            <span className="text-sm text-[var(--text-2)] flex-1 font-medium">{seg.label}</span>
            <span
              className="text-xl font-black font-mono"
              style={{ color: seg.color }}
            >
              {seg.pct}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
