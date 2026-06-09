import { useState, useMemo } from 'react'
import type { SurveyResponse } from '../types'

interface Props {
  data: SurveyResponse[]
}

export default function ResponseTable({ data }: Props) {
  const [categoryFilter, setCategoryFilter] = useState('')
  const [deliveryFilter, setDeliveryFilter] = useState('')
  const [search, setSearch] = useState('')

  const categories = useMemo(
    () => Array.from(new Set(data.map((r) => r.category))).sort(),
    [data]
  )

  const filtered = useMemo(() => {
    return data.filter((r) => {
      if (categoryFilter && r.category !== categoryFilter) return false
      if (deliveryFilter) {
        const match = deliveryFilter === 'yes' ? 'yes' : 'no'
        if (r.delivery.toLowerCase() !== match) return false
      }
      if (search) {
        const q = search.toLowerCase()
        if (
          !r.respondent_id.toLowerCase().includes(q) &&
          !r.improvement.toLowerCase().includes(q)
        )
          return false
      }
      return true
    })
  }, [data, categoryFilter, deliveryFilter, search])

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-4">
        <h2 className="text-sm font-medium text-gray-700 flex-1">
          Responses{' '}
          <span className="text-gray-400 font-normal">({filtered.length} shown)</span>
        </h2>
        <input
          type="text"
          placeholder="Search ID or feedback..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 w-full sm:w-56 focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-300"
        >
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          value={deliveryFilter}
          onChange={(e) => setDeliveryFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-300"
        >
          <option value="">All delivery</option>
          <option value="yes">On Time</option>
          <option value="no">Delayed</option>
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-400 uppercase tracking-wide border-b border-gray-100">
              <th className="pb-2 pr-4 font-medium">ID</th>
              <th className="pb-2 pr-4 font-medium">Satisfaction</th>
              <th className="pb-2 pr-4 font-medium">NPS</th>
              <th className="pb-2 pr-4 font-medium">Category</th>
              <th className="pb-2 pr-4 font-medium">Delivery</th>
              <th className="pb-2 font-medium">Improvement Feedback</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-gray-400 text-sm">
                  No responses match the current filters.
                </td>
              </tr>
            )}
            {filtered.map((r) => (
              <tr
                key={r.respondent_id}
                className="border-b border-gray-50 hover:bg-gray-50 transition-colors"
              >
                <td className="py-2 pr-4 font-mono text-gray-600">{r.respondent_id}</td>
                <td className="py-2 pr-4">
                  <SatisfactionBadge score={r.satisfaction} />
                </td>
                <td className="py-2 pr-4 text-gray-700">{r.nps}</td>
                <td className="py-2 pr-4 text-gray-700">{r.category}</td>
                <td className="py-2 pr-4">
                  <span
                    className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${
                      r.delivery.toLowerCase() === 'yes'
                        ? 'bg-green-50 text-green-700'
                        : 'bg-red-50 text-red-600'
                    }`}
                  >
                    {r.delivery.toLowerCase() === 'yes' ? 'On Time' : 'Delayed'}
                  </span>
                </td>
                <td className="py-2 text-gray-500 max-w-xs truncate">
                  {r.improvement || <span className="text-gray-300">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SatisfactionBadge({ score }: { score: number }) {
  const color =
    score >= 4
      ? 'bg-green-50 text-green-700'
      : score === 3
      ? 'bg-amber-50 text-amber-700'
      : 'bg-red-50 text-red-600'
  return (
    <span className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>
      {score}
    </span>
  )
}
