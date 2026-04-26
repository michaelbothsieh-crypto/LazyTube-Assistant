export default function SentimentMeter({
  sentiment
}: { sentiment: { bullish: number; bearish: number; neutral: number } }) {
  const { bullish, bearish, neutral } = sentiment
  const total = bullish + bearish + neutral

  return (
    <div className="glass p-5">
      <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
        📊 <span>今日 KOL 情緒</span>
      </h2>

      {/* 三色條 */}
      <div className="h-3 rounded-full overflow-hidden flex mb-4">
        <div style={{ width: `${bullish}%`, background: '#10b981' }} className="transition-all duration-700" />
        <div style={{ width: `${neutral}%`, background: '#475569' }} className="transition-all duration-700" />
        <div style={{ width: `${bearish}%`, background: '#ef4444' }} className="transition-all duration-700" />
      </div>

      {/* 數字 */}
      <div className="space-y-2">
        {([
          { label: '多方看好', pct: bullish, color: '#10b981', icon: '🐂' },
          { label: '中性觀望', pct: neutral, color: '#475569', icon: '⚖️' },
          { label: '空方謹慎', pct: bearish, color: '#ef4444', icon: '🐻' },
        ] as const).map(item => (
          <div key={item.label} className="flex items-center gap-2 text-xs">
            <span>{item.icon}</span>
            <span className="text-slate-400 flex-1">{item.label}</span>
            <span className="font-mono font-semibold" style={{ color: item.color }}>{item.pct}%</span>
          </div>
        ))}
      </div>

      {/* 主看法 */}
      <div className="mt-4 p-3 rounded-lg" style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.15)' }}>
        <p className="text-xs text-emerald-400 font-medium">
          {bullish > 60 ? '📈 多數 KOL 今日看多' : bullish > 40 ? '📊 市場情緒偏中性' : '📉 KOL 今日趨於保守'}
        </p>
      </div>
    </div>
  )
}
