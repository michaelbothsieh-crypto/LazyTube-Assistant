const SIZES = [
  'text-xl font-black', 'text-lg font-bold', 'text-base font-semibold',
  'text-sm font-medium', 'text-xs font-normal',
]
const COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4',
  '#ec4899', '#84cc16', '#f97316',
]

export default function KeywordCloud({ keywords }: { keywords: string[] }) {
  return (
    <div className="glass p-5">
      <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
        🏷️ <span>本週熱門關鍵詞</span>
      </h2>
      <div className="flex flex-wrap gap-2 justify-center">
        {keywords.map((kw, i) => (
          <span
            key={kw}
            className={`${SIZES[Math.min(i, SIZES.length - 1)]} px-3 py-1.5 rounded-lg cursor-default select-none transition-all hover:scale-110`}
            style={{
              color: COLORS[i % COLORS.length],
              background: `${COLORS[i % COLORS.length]}15`,
              border: `1px solid ${COLORS[i % COLORS.length]}30`,
            }}
          >
            {kw}
          </span>
        ))}
      </div>
    </div>
  )
}
