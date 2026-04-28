import { TrendUp, TrendDown, Minus } from '@/components/icons'

type Sentiment = { bullish: number; bearish: number; neutral: number }

interface Props {
  score: number
  theme: string
  date: string
  sentiment: Sentiment
  episodesCount: number
}

export default function HeroConsensus({ score, theme, date, sentiment, episodesCount }: Props) {
  const scoreColor  = score >= 75 ? 'var(--bullish)' : score >= 50 ? '#d97706' : 'var(--bearish)'
  const scoreLabel  = score >= 75 ? '強烈共識' : score >= 50 ? '溫和共識' : '分歧觀點'
  const scoreBg     = score >= 75 ? 'var(--bullish-bg)' : score >= 50 ? '#fffbeb' : 'var(--bearish-bg)'
  const scoreBorder = score >= 75 ? 'var(--bullish-border)' : score >= 50 ? '#fde68a' : 'var(--bearish-border)'

  const SentIcon  = sentiment.bullish >= 50 ? TrendUp : sentiment.bearish >= 50 ? TrendDown : Minus
  const sentLabel = sentiment.bullish >= 50 ? '多方主導' : sentiment.bearish >= 50 ? '空方主導' : '情緒中性'

  const stats = [
    {
      label: '共識分數',
      value: String(score),
      sub: scoreLabel,
      color: scoreColor,
      bg: scoreBg,
      border: scoreBorder,
      large: true,
    },
    {
      label: '多方 KOL',
      value: `${sentiment.bullish}%`,
      sub: '看多佔比',
      color: 'var(--bullish)',
      bg: 'var(--bullish-bg)',
      border: 'var(--bullish-border)',
    },
    {
      label: '空方 KOL',
      value: `${sentiment.bearish}%`,
      sub: '看空佔比',
      color: 'var(--bearish)',
      bg: 'var(--bearish-bg)',
      border: 'var(--bearish-border)',
    },
    {
      label: '今日集數',
      value: String(episodesCount),
      sub: '已完成分析',
      color: 'var(--accent)',
      bg: 'var(--accent-bg)',
      border: 'var(--accent-border)',
    },
  ]

  return (
    <section className="space-y-5 scale-in">
      {/* Theme header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <p className="section-label mb-2">{date} · 今日市場主題</p>
          <h1 className="text-xl sm:text-2xl font-bold text-[var(--text-1)] leading-snug max-w-2xl">
            {theme}
          </h1>
        </div>
        <div
          className="inline-flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-full flex-shrink-0"
          style={{ background: scoreBg, border: `1px solid ${scoreBorder}`, color: scoreColor }}
        >
          <SentIcon size={16} />
          {sentLabel}
        </div>
      </div>

      {/* Stat tiles row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(s => (
          <div
            key={s.label}
            className="card p-5"
            style={{ borderTop: `3px solid ${s.color}` }}
          >
            <p className="section-label mb-3">{s.label}</p>
            <p
              className="font-black font-mono leading-none mb-1.5"
              style={{
                fontSize: s.large ? '3rem' : '2.2rem',
                color: s.color,
              }}
            >
              {s.value}
            </p>
            <p className="text-xs text-[var(--text-3)] font-medium">{s.sub}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
