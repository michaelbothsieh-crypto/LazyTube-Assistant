import type { Stock } from '@/types'
import { TrendUp, TrendDown, Minus } from '@/components/icons'

const SENT_CONFIG = {
  bullish: { label: '多方看好', color: 'var(--bullish)', bg: 'var(--bullish-bg)', border: 'var(--bullish-border)', Icon: TrendUp },
  bearish: { label: '空方謹慎', color: 'var(--bearish)', bg: 'var(--bearish-bg)', border: 'var(--bearish-border)', Icon: TrendDown },
  neutral: { label: '中性觀望', color: 'var(--neutral)', bg: 'var(--neutral-bg)', border: 'var(--neutral-border)', Icon: Minus },
} as const

const MAX_MENTIONS = 10

export default function StockRanking({ stocks }: { stocks: Stock[] }) {
  return (
    <div className="card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5 pb-4 border-b" style={{ borderColor: 'var(--border)' }}>
        <div>
          <p className="section-label mb-1">今日共識標的</p>
          <p className="text-base font-bold text-[var(--text-1)]">KOL 提及熱度排行</p>
        </div>
        <span className="text-xs text-[var(--text-4)] font-mono">{stocks.length} 支標的</span>
      </div>

      {/* Column headers */}
      <div
        className="grid gap-3 px-2 mb-2"
        style={{ gridTemplateColumns: '28px 80px 1fr 100px 80px 100px' }}
      >
        {['#', '代碼', '名稱', '情緒', '提及', '熱度'].map(h => (
          <span key={h} className="section-label">{h}</span>
        ))}
      </div>

      {/* Rows */}
      <div>
        {stocks.map((s, i) => {
          const sc = SENT_CONFIG[s.sentiment]
          const pct = Math.min(100, Math.round((s.mentions / MAX_MENTIONS) * 100))

          return (
            <div
              key={s.ticker}
              className="group grid gap-3 items-center px-2 py-3 rounded-lg transition-colors duration-150 hover:cursor-default hover:bg-[var(--surface-2)]"
              style={{
                gridTemplateColumns: '28px 80px 1fr 100px 80px 100px',
                borderBottom: i < stocks.length - 1 ? '1px solid var(--border)' : 'none',
              }}
            >
              {/* Rank */}
              <span className="text-sm font-mono font-semibold text-[var(--text-4)] text-right">{i + 1}</span>

              {/* Ticker */}
              <span className={s.market === 'TW' ? 'ticker-tw' : 'ticker-us'}>{s.ticker}</span>

              {/* Name */}
              <span className="text-sm font-medium text-[var(--text-2)] truncate">{s.name}</span>

              {/* Sentiment badge */}
              <span
                className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-semibold w-fit"
                style={{ background: sc.bg, border: `1px solid ${sc.border}`, color: sc.color }}
              >
                <sc.Icon size={12} />
                {s.sentiment === 'bullish' ? '多' : s.sentiment === 'bearish' ? '空' : '中'}
              </span>

              {/* Count */}
              <span
                className="text-base font-black font-mono text-right"
                style={{ color: sc.color }}
              >
                {s.mentions}x
              </span>

              {/* Mini bar */}
              <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                <div
                  className="h-full rounded-full bar-fill"
                  style={{
                    '--w': `${pct}%`,
                    width: `${pct}%`,
                    background: sc.color,
                  } as React.CSSProperties}
                />
              </div>
            </div>
          )
        })}
      </div>

      {/* KOL list on hover — shown below table on mobile as a note */}
      <p className="mt-4 text-xs text-[var(--text-4)] font-mono">
        * 懸停行可查看引用該標的的 KOL 列表
      </p>
    </div>
  )
}
