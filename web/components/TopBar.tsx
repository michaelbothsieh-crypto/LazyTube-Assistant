'use client'
export default function TopBar({
  date, generatedAt, episodesCount
}: { date: string; generatedAt: string; episodesCount: number }) {
  const time = generatedAt ? new Date(generatedAt).toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' }) : ''
  return (
    <header className="sticky top-0 z-50 border-b border-[rgba(59,130,246,0.12)]"
      style={{ background: 'rgba(6,13,31,0.92)', backdropFilter: 'blur(20px)' }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">

        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-sm font-bold">P</div>
          <span className="font-bold text-white tracking-tight">PodConsensus</span>
          <span className="hidden sm:block text-xs text-slate-500 border border-slate-700 rounded px-2 py-0.5">財經 KOL 共識儀表板</span>
        </div>

        {/* 狀態 */}
        <div className="flex items-center gap-4 text-xs text-slate-400">
          <span className="hidden sm:flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 live-dot inline-block" />
            今日分析 {episodesCount} 集
          </span>
          <span className="font-mono">{date}</span>
          {time && <span className="text-slate-600 hidden md:block">更新 {time}</span>}
        </div>
      </div>
    </header>
  )
}
