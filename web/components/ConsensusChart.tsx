'use client'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from 'recharts'
import type { ConsensusHistory } from '@/types'
import { Activity } from '@/components/icons'

export default function ConsensusChart({ history }: { history: ConsensusHistory[] }) {
  const sorted = [...history].sort((a, b) => a.date.localeCompare(b.date))
  const latest = sorted[sorted.length - 1]?.score ?? 0
  const prev   = sorted[sorted.length - 2]?.score ?? 0
  const delta  = latest - prev
  const deltaColor = delta >= 0 ? 'var(--bullish)' : 'var(--bearish)'

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between mb-6">
        <div>
          <p className="section-label mb-1">共識走勢</p>
          <div className="flex items-center gap-2 mt-2">
            <Activity size={18} style={{ color: 'var(--accent)' }} />
            <p className="text-base font-bold text-[var(--text-1)]">近 7 日共識指數變化</p>
          </div>
        </div>
        <div className="text-right">
          <p className="section-label mb-1">今日分數</p>
          <div className="flex items-baseline gap-2 justify-end">
            <span className="text-3xl font-black font-mono" style={{ color: 'var(--accent)' }}>{latest}</span>
            {delta !== 0 && (
              <span className="text-sm font-bold font-mono" style={{ color: deltaColor }}>
                {delta > 0 ? '+' : ''}{delta}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={sorted} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <defs>
              <linearGradient id="accentGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#2563eb" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="4 4" stroke="var(--border)" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'JetBrains Mono' }}
              tickFormatter={d => d.slice(5)}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'JetBrains Mono' }}
              axisLine={false}
              tickLine={false}
              domain={[0, 100]}
            />
            <ReferenceLine y={50} stroke="var(--border-strong)" strokeDasharray="4 4" label={{ value: '中性', fill: '#94a3b8', fontSize: 10 }} />
            <Tooltip
              contentStyle={{
                background: '#ffffff',
                border: '1px solid var(--border)',
                borderRadius: 10,
                fontSize: 13,
                fontFamily: 'JetBrains Mono',
                boxShadow: '0 4px 12px rgba(15,23,42,0.08)',
              }}
              labelStyle={{ color: '#64748b' }}
              itemStyle={{ color: '#2563eb', fontWeight: 700 }}
              formatter={(v) => [`${v ?? ''}`, '共識分數']}
            />
            <Area
              type="monotone"
              dataKey="score"
              stroke="#2563eb"
              strokeWidth={2.5}
              fill="url(#accentGrad)"
              dot={{ fill: '#2563eb', r: 3.5, strokeWidth: 0 }}
              activeDot={{ fill: '#2563eb', r: 5, strokeWidth: 2, stroke: '#fff' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
