import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts'
import type { SurveyResponse } from '../types'

interface Props {
  data: SurveyResponse[]
}

export default function SatisfactionChart({ data }: Props) {
  const counts: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 }
  data.forEach((r) => {
    if (r.satisfaction >= 1 && r.satisfaction <= 5) counts[r.satisfaction]++
  })

  const chartData = [1, 2, 3, 4, 5].map((score) => ({
    score: String(score),
    count: counts[score],
  }))

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <h2 className="text-sm font-medium text-gray-700 mb-4">Satisfaction Distribution</h2>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} barSize={32}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="score" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
