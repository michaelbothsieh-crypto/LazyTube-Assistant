export default function HeroConsensus({
  score, theme, date
}: { score: number; theme: string; date: string }) {
  const scoreColor = score >= 75 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444'
  const label = score >= 75 ? '強烈共識' : score >= 50 ? '溫和共識' : '分歧觀點'

  return (
    <section className="glass p-6 sm:p-8 relative overflow-hidden fade-up">
      {/* 背景光效 */}
      <div className="absolute inset-0 pointer-events-none"
        style={{ background: `radial-gradient(ellipse 60% 80% at 20% 50%, ${scoreColor}0a 0%, transparent 60%)` }} />

      <div className="relative flex flex-col sm:flex-row items-start sm:items-center gap-6">
        {/* 共識分數環 */}
        <div className="relative flex-shrink-0">
          <svg width="100" height="100" className="rotate-[-90deg]">
            <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
            <circle
              cx="50" cy="50" r="42" fill="none"
              stroke={scoreColor} strokeWidth="8"
              strokeDasharray={`${2 * Math.PI * 42 * score / 100} ${2 * Math.PI * 42}`}
              strokeLinecap="round"
              style={{ transition: 'stroke-dasharray 1s ease' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-black" style={{ color: scoreColor }}>{score}</span>
            <span className="text-[10px] text-slate-400 mt-0.5">{label}</span>
          </div>
        </div>

        {/* 主題文字 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-mono text-blue-400 uppercase tracking-widest">今日市場主題</span>
            <span className="text-[10px] text-slate-600">{date}</span>
          </div>
          <h1 className="text-lg sm:text-xl font-bold text-white leading-snug">{theme}</h1>
          <p className="mt-2 text-sm text-slate-400">
            綜合 12 位財經 KOL 今日節目分析，共識指數反映整體看多比例
          </p>
        </div>
      </div>
    </section>
  )
}
