import type { ConsensusHistory } from '@/types'

export default function ConsensusChart({ history }: { history: ConsensusHistory[] }) {
  const sorted = [...history].sort((a, b) => a.date.localeCompare(b.date)).slice(-14)
  const width = 720
  const height = 260
  const padding = { top: 20, right: 18, bottom: 34, left: 34 }
  const innerWidth = width - padding.left - padding.right
  const innerHeight = height - padding.top - padding.bottom
  const points = sorted.map((item, index) => {
    const x = padding.left + (sorted.length <= 1 ? 0 : (index / (sorted.length - 1)) * innerWidth)
    const y = padding.top + (1 - Math.max(0, Math.min(100, item.score)) / 100) * innerHeight
    return { ...item, x, y }
  })
  const line = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(' ')
  const area = points.length
    ? `${line} L ${points[points.length - 1].x.toFixed(2)} ${height - padding.bottom} L ${points[0].x.toFixed(2)} ${height - padding.bottom} Z`
    : ''
  const latest = points[points.length - 1]?.score ?? 0
  const previous = points[points.length - 2]?.score ?? latest
  const delta = latest - previous

  return (
    <div className="chart-panel">
      <div className="chart-header">
        <div>
          <span className="card-label">市場方向變化</span>
          <strong>{latest}</strong>
        </div>
        <small className={delta >= 0 ? 'chart-up' : 'chart-down'}>
          {delta >= 0 ? '+' : ''}{delta}
        </small>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="市場方向歷史圖">
        <defs>
          <linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#73f1ba" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#73f1ba" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 25, 50, 75, 100].map((tick) => {
          const y = padding.top + (1 - tick / 100) * innerHeight
          return (
            <g key={tick}>
              <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} className="chart-grid" />
              <text x={10} y={y + 4} className="chart-tick">{tick}</text>
            </g>
          )
        })}
        {area && <path d={area} fill="url(#chartFill)" />}
        {line && <path d={line} className="chart-line" />}
        {points.map((point) => (
          <g key={point.date}>
            <circle cx={point.x} cy={point.y} r="4" className="chart-dot" />
            <text x={point.x} y={height - 10} textAnchor="middle" className="chart-date">
              {point.date.slice(5)}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}
