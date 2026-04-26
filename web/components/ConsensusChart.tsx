'use client'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { ConsensusHistory } from '@/types'

export default function ConsensusChart({ history }: { history: ConsensusHistory[] }) {
  const sorted = [...history].sort((a, b) => a.date.localeCompare(b.date))

  return (
    <div className="glass p-5">
      <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
        📈 <span>近 7 日共識指數趨勢</span>
      </h2>
      <div className="h-36">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={sorted} margin={{ top: 4, right: 4, left: -32, bottom: 0 }}>
            <defs>
              <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              tick={{ fill: '#475569', fontSize: 10, fontFamily: 'monospace' }}
              tickFormatter={d => d.slice(5)}
              axisLine={false} tickLine={false}
            />
            <YAxis domain={[0, 100]} hide />
            <Tooltip
              contentStyle={{ background: '#0d1b35', border: '1px solid rgba(59,130,246,0.2)', borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: '#94a3b8' }}
              itemStyle={{ color: '#3b82f6' }}
              formatter={(v: number) => [`${v}`, '共識指數']}
            />
            <Area
              type="monotone" dataKey="score"
              stroke="#3b82f6" strokeWidth={2}
              fill="url(#cg)" dot={{ fill: '#3b82f6', r: 3, strokeWidth: 0 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
