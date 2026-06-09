import { useState, useEffect, useCallback } from 'react'
import type { SurveyResponse } from '../types'

function parseCSV(text: string): SurveyResponse[] {
  const lines = text.trim().split('\n')
  // skip header
  return lines.slice(1).map((line) => {
    // handle quoted fields that may contain commas
    const cols: string[] = []
    let current = ''
    let inQuotes = false
    for (let i = 0; i < line.length; i++) {
      const ch = line[i]
      if (ch === '"') {
        inQuotes = !inQuotes
      } else if (ch === ',' && !inQuotes) {
        cols.push(current.trim())
        current = ''
      } else {
        current += ch
      }
    }
    cols.push(current.trim())

    return {
      respondent_id: cols[0] ?? '',
      satisfaction: parseInt(cols[1] ?? '0', 10),
      nps: parseInt(cols[2] ?? '0', 10),
      category: cols[3] ?? '',
      delivery: cols[4] ?? '',
      improvement: cols[5] ?? '',
    }
  }).filter((r) => r.respondent_id !== '')
}

export function useResponses() {
  const [data, setData] = useState<SurveyResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Re-fetch responses.csv from the host, bypassing any cache so the latest
  // data always shows. Used on first mount and after a generate run.
  const reload = useCallback(async () => {
    setError(null)
    try {
      const res = await fetch(`/responses.csv?t=${Date.now()}`, { cache: 'no-store' })
      if (!res.ok) throw new Error(`Failed to load responses.csv (${res.status})`)
      const text = await res.text()
      setData(parseCSV(text))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  // Ask the backend to run generate.py, then reload the fresh CSV. Needs the
  // backend running (python server.py, or `npm run dev`). On a plain static
  // host there is no backend, so this surfaces a clear error.
  const generate = useCallback(async () => {
    setGenerating(true)
    setError(null)
    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok || !body.ok) {
        throw new Error(body.error || `Generation failed (${res.status}). Is the backend running?`)
      }
      await reload()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setGenerating(false)
    }
  }, [reload])

  useEffect(() => {
    void reload()
  }, [reload])

  return { data, loading, generating, error, generate }
}
