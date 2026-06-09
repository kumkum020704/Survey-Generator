import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
// The single source of truth: the responses.csv that generate.py writes,
// one level up at the project root. The dashboard never keeps its own copy.
const PROJECT_ROOT = path.resolve(here, '..')
const ROOT_CSV = path.resolve(PROJECT_ROOT, 'responses.csv')

// `python` on most systems, `py` is the Windows launcher fallback.
const PYTHON = process.env.PYTHON_BIN || 'python'

// Serve /responses.csv from the project root in dev, expose a POST /api/generate
// that actually runs generate.py, and copy the CSV into dist on build — so the
// dashboard always reflects the latest generation with no manual copying.
function rootResponses() {
  return {
    name: 'root-responses-csv',
    configureServer(server: any) {
      server.middlewares.use('/responses.csv', (_req: any, res: any) => {
        try {
          const data = fs.readFileSync(ROOT_CSV)
          res.setHeader('Content-Type', 'text/csv; charset=utf-8')
          res.setHeader('Cache-Control', 'no-store') // always fetch fresh
          res.end(data)
        } catch {
          res.statusCode = 404
          res.end('responses.csv not found at project root — run generate.py first')
        }
      })

      // Re-run generate.py and report the outcome as JSON. Triggered by the
      // dashboard's "Generate" button.
      server.middlewares.use('/api/generate', (req: any, res: any) => {
        if (req.method !== 'POST') {
          res.statusCode = 405
          res.end('Use POST')
          return
        }
        const proc = spawn(PYTHON, ['generate.py'], { cwd: PROJECT_ROOT })
        let stderr = ''
        proc.stderr.on('data', (d: Buffer) => { stderr += d.toString() })
        proc.on('error', (err: Error) => {
          res.statusCode = 500
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ ok: false, error: `Could not start Python: ${err.message}` }))
        })
        proc.on('close', (code: number) => {
          res.setHeader('Content-Type', 'application/json')
          if (code === 0) {
            res.end(JSON.stringify({ ok: true, log: stderr.trim() }))
          } else {
            res.statusCode = 500
            res.end(JSON.stringify({ ok: false, error: stderr.trim() || `generate.py exited ${code}` }))
          }
        })
      })
    },
    closeBundle() {
      try {
        fs.copyFileSync(ROOT_CSV, path.resolve(here, 'dist', 'responses.csv'))
      } catch {
        /* root CSV missing at build time — dist will just lack the file */
      }
    },
  }
}

export default defineConfig({
  plugins: [react(), rootResponses()],
})
