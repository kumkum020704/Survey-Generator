import type { SurveyResponse } from '../types'

interface Props {
  data: SurveyResponse[]
}

function Card({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-3xl font-semibold text-gray-900">{value}</p>
      {sub && <p className="mt-1 text-xs text-gray-400">{sub}</p>}
    </div>
  )
}

export default function MetricsCards({ data }: Props) {
  const total = data.length

  const avgSatisfaction =
    total > 0
      ? (data.reduce((s, r) => s + r.satisfaction, 0) / total).toFixed(2)
      : '—'

  const promoters = data.filter((r) => r.nps >= 9).length
  const detractors = data.filter((r) => r.nps <= 6).length
  const nps =
    total > 0 ? Math.round(((promoters - detractors) / total) * 100) : 0

  const onTime = data.filter((r) => r.delivery.toLowerCase() === 'yes').length
  const onTimePct = total > 0 ? Math.round((onTime / total) * 100) : 0

  // Coherence: check if satisfaction and NPS are directionally consistent
  const coherent = data.filter((r) => {
    if (r.satisfaction >= 4 && r.nps >= 7) return true
    if (r.satisfaction <= 2 && r.nps <= 6) return true
    if (r.satisfaction === 3) return true
    return false
  }).length
  const coherencePct = total > 0 ? Math.round((coherent / total) * 100) : 0
  const coherenceLabel = coherencePct >= 80 ? 'Pass' : 'Review'

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
      <Card label="Total Responses" value={String(total)} />
      <Card label="Avg Satisfaction" value={avgSatisfaction} sub="out of 5" />
      <Card
        label="NPS Score"
        value={total > 0 ? String(nps) : '—'}
        sub={`${promoters} promoters · ${detractors} detractors`}
      />
      <Card label="On-Time Delivery" value={total > 0 ? `${onTimePct}%` : '—'} />
      <Card
        label="Coherence"
        value={coherenceLabel}
        sub={`${coherencePct}% consistent`}
      />
    </div>
  )
}
