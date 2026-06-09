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

export default function CategoryChart({ data }: Props) {
  const counts: Record<string, number> = {}
  data.forEach((r) => {
    if (r.category) counts[r.category] = (counts[r.category] ?? 0) + 1
  })

  const chartData = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({ name, count }))

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <h2 className="text-sm font-medium text-gray-700 mb-4">Responses by Category</h2>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} layout="vertical" barSize={20}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={80} />
          <Tooltip />
          <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
