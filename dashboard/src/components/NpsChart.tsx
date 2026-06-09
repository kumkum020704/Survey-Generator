import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { SurveyResponse } from '../types'

interface Props {
  data: SurveyResponse[]
}

function npsColor(score: number): string {
  if (score >= 9) return '#22c55e'
  if (score >= 7) return '#f59e0b'
  return '#ef4444'
}

export default function NpsChart({ data }: Props) {
  const counts: Record<number, number> = {}
  for (let i = 0; i <= 10; i++) counts[i] = 0
  data.forEach((r) => {
    if (r.nps >= 0 && r.nps <= 10) counts[r.nps]++
  })

  const chartData = Array.from({ length: 11 }, (_, i) => ({
    score: String(i),
    count: counts[i],
    raw: i,
  }))

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <h2 className="text-sm font-medium text-gray-700 mb-1">NPS Distribution</h2>
      <p className="text-xs text-gray-400 mb-4">
        <span className="text-red-400">■</span> Detractor (0–6) &nbsp;
        <span className="text-amber-400">■</span> Passive (7–8) &nbsp;
        <span className="text-green-500">■</span> Promoter (9–10)
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} barSize={20}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="score" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {chartData.map((entry) => (
              <Cell key={entry.score} fill={npsColor(entry.raw)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
