import type { Episode } from '@/types'

const SENTIMENT_CONFIG = {
  bullish: { label: '🐂 多方', cls: 'pill-bullish' },
  bearish: { label: '🐻 空方', cls: 'pill-bearish' },
  neutral: { label: '⚖️ 中立', cls: 'pill-neutral' },
}

export default function KOLGrid({ episodes }: { episodes: Episode[] }) {
  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          📻 <span>今日更新頻道</span>
        </h2>
        <span className="text-xs text-slate-500">{episodes.length} 集已分析</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {episodes.map((ep, i) => {
          const sc = SENTIMENT_CONFIG[ep.sentiment]
          return (
            <div
              key={`${ep.kol_id}-${i}`}
              className="glass p-4 flex flex-col gap-3 fade-up"
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              {/* 頭部：頻道名 + 情緒 */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xl leading-none flex-shrink-0">{ep.avatar}</span>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-white truncate">{ep.kol_name}</p>
                    <p className="text-[10px] text-slate-500">{ep.host}</p>
                  </div>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full flex-shrink-0 ${sc.cls}`}>
                  {sc.label}
                </span>
              </div>

              {/* 節目標題 */}
              <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">{ep.title}</p>

              {/* 摘要 */}
              <p className="text-[11px] text-slate-500 line-clamp-3 leading-relaxed flex-1">{ep.summary}</p>

              {/* 底部：標的 + 日期 */}
              <div className="flex items-center justify-between gap-2 pt-2 border-t border-white/5">
                <div className="flex flex-wrap gap-1">
                  {ep.stocks_mentioned.slice(0, 3).map(t => (
                    <span key={t} className={/^\d/.test(t) ? 'ticker-tw' : 'ticker-us'}>{t}</span>
                  ))}
                </div>
                <span className="text-[10px] text-slate-600 font-mono flex-shrink-0">{ep.published}</span>
              </div>

              {/* 完整報告連結 */}
              {ep.report_url && (
                <a
                  href={ep.report_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1"
                >
                  📄 查看完整 AI 分析報告 →
                </a>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
