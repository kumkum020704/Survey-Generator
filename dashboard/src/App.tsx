import { useResponses } from './hooks/useResponses'
import Header from './components/Header'
import MetricsCards from './components/MetricsCards'
import SatisfactionChart from './components/SatisfactionChart'
import NpsChart from './components/NpsChart'
import CategoryChart from './components/CategoryChart'
import DeliveryChart from './components/DeliveryChart'
import ResponseTable from './components/ResponseTable'

export default function App() {
  const { data, loading, generating, error, generate } = useResponses()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400 text-sm">
        Loading responses...
      </div>
    )
  }

  // Initial-load failure (no data at all): full-screen message.
  if (error && data.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 font-medium mb-1">Could not load responses.csv</p>
          <p className="text-sm text-gray-400">{error}</p>
          <p className="text-xs text-gray-400 mt-2">
            Run <code>python generate.py</code> (or click Generate with the backend running).
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-6xl mx-auto px-6 py-10">
        <Header onGenerate={generate} generating={generating} />
        {/* Generate failed but we still have data to show: inline banner. */}
        {error && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </div>
        )}
        <MetricsCards data={data} />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <SatisfactionChart data={data} />
          <NpsChart data={data} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <CategoryChart data={data} />
          <DeliveryChart data={data} />
        </div>
        <ResponseTable data={data} />
      </div>
    </div>
  )
}
