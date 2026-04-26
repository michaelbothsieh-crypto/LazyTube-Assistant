import type { Stock } from '@/types'

const MAX_MENTIONS = 10

export default function StockRanking({ stocks }: { stocks: Stock[] }) {
  return (
    <div className="glass p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          🔥 <span>今日共識標的</span>
        </h2>
        <span className="text-xs text-slate-500">KOL 提及次數排行</span>
      </div>

      <div className="space-y-3">
        {stocks.map((s, i) => {
          const pct = Math.round((s.mentions / MAX_MENTIONS) * 100)
          const barColor = s.sentiment === 'bullish' ? '#10b981'
            : s.sentiment === 'bearish' ? '#ef4444' : '#64748b'
          const pillClass = s.sentiment === 'bullish' ? 'pill-bullish'
            : s.sentiment === 'bearish' ? 'pill-bearish' : 'pill-neutral'
          const pillLabel = s.sentiment === 'bullish' ? '多' : s.sentiment === 'bearish' ? '空' : '中'

          return (
            <div key={s.ticker} className="group">
              <div className="flex items-center gap-3 mb-1.5">
                {/* 排名 */}
                <span className="text-xs font-mono text-slate-600 w-4 text-right">{i + 1}</span>

                {/* 代號 + 市場 */}
                <span className={s.market === 'TW' ? 'ticker-tw' : 'ticker-us'}>{s.ticker}</span>
                <span className="text-xs text-slate-300 flex-1 truncate">{s.name}</span>

                {/* 情緒 */}
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${pillClass}`}>{pillLabel}</span>

                {/* 提及次數 */}
                <span className="text-xs font-mono font-semibold" style={{ color: barColor }}>
                  {s.mentions}
                </span>
              </div>

              {/* 進度條 */}
              <div className="ml-7 h-1.5 bg-white/5 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${pct}%`, background: barColor, opacity: 0.7 }}
                />
              </div>

              {/* KOL 標籤（hover 顯示） */}
              <div className="ml-7 mt-1 flex flex-wrap gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {s.kols.slice(0, 4).map(k => (
                  <span key={k} className="text-[10px] text-slate-500 bg-white/5 rounded px-1.5 py-0.5">{k}</span>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
