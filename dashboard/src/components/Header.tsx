interface HeaderProps {
  onGenerate: () => void
  generating: boolean
}

export default function Header({ onGenerate, generating }: HeaderProps) {
  return (
    <div className="mb-8 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 tracking-tight">
          Synthetic Survey Response Generator
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          LLM-generated survey responses with persona-aware coherence validation —
          an analysis of simulated customer feedback data.
        </p>
      </div>
      <button
        onClick={onGenerate}
        disabled={generating}
        className="shrink-0 inline-flex items-center gap-2 rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
        title="Run generate.py and reload the dashboard"
      >
        <span
          className={generating ? 'inline-block animate-spin' : 'inline-block'}
          aria-hidden
        >
          ↻
        </span>
        {generating ? 'Generating…' : 'Generate'}
      </button>
    </div>
  )
}
