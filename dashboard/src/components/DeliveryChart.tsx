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

export default function DeliveryChart({ data }: Props) {
  const onTime = data.filter((r) => r.delivery.toLowerCase() === 'yes').length
  const delayed = data.filter((r) => r.delivery.toLowerCase() === 'no').length

  const chartData = [
    { label: 'On Time', count: onTime },
    { label: 'Delayed', count: delayed },
  ]

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <h2 className="text-sm font-medium text-gray-700 mb-4">Delivery Status</h2>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} barSize={48}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            <Cell fill="#22c55e" />
            <Cell fill="#ef4444" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
