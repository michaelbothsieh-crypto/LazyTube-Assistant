import { Tag } from '@/components/icons'

const COLORS = [
  { text: 'var(--accent)',   bg: 'var(--accent-bg)',   border: 'var(--accent-border)'   },
  { text: 'var(--bullish)',  bg: 'var(--bullish-bg)',  border: 'var(--bullish-border)'  },
  { text: '#b45309',         bg: '#fffbeb',            border: '#fde68a'                },
  { text: '#7c3aed',         bg: '#f5f3ff',            border: '#ddd6fe'                },
  { text: '#0891b2',         bg: '#ecfeff',            border: '#a5f3fc'                },
]

const WEIGHT = ['text-lg font-black', 'text-base font-bold', 'text-sm font-semibold', 'text-sm font-medium', 'text-xs font-medium']

export default function KeywordCloud({ keywords }: { keywords: string[] }) {
  return (
    <div className="card p-6 flex flex-col gap-4">
      <div>
        <p className="section-label mb-1">熱門關鍵詞</p>
        <div className="flex items-center gap-2 mt-2">
          <Tag size={16} style={{ color: 'var(--text-3)' }} />
          <p className="text-base font-bold text-[var(--text-1)]">本期討論焦點</p>
        </div>
      </div>

      {keywords.length === 0 ? (
        <p className="text-sm text-[var(--text-4)] py-4 text-center">暫無資料</p>
      ) : (
        <div className="flex flex-wrap gap-2.5">
          {keywords.map((kw, i) => {
            const c = COLORS[i % COLORS.length]
            const w = WEIGHT[Math.min(i, WEIGHT.length - 1)]
            return (
              <span
                key={kw}
                className={`${w} px-3 py-1.5 rounded-lg select-none cursor-default transition-transform duration-150 hover:scale-105 hover:-translate-y-0.5`}
                style={{ color: c.text, background: c.bg, border: `1px solid ${c.border}` }}
              >
                {kw}
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}
