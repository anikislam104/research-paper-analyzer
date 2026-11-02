import { useEffect, useState } from 'react'

// Typical single-call durations (seconds) on a 6 GB GPU, used until real runs have been recorded.
const DEFAULT_SECONDS: Record<string, number> = {
  oneline: 12,
  scope: 8,
  results: 15,
  dataset: 12,
  limitations: 10,
  diagram: 18,
}

const key = (mode: string) => `pa-durations-${mode}`

export function recordDuration(mode: string, seconds: number) {
  try {
    const past: number[] = JSON.parse(localStorage.getItem(key(mode)) ?? '[]')
    localStorage.setItem(key(mode), JSON.stringify([...past, seconds].slice(-5)))
  } catch {
    /* storage unavailable: fall back to defaults */
  }
}

function typicalSeconds(mode: string): number {
  try {
    const past: number[] = JSON.parse(localStorage.getItem(key(mode)) ?? '[]')
    if (past.length) return past.reduce((a, b) => a + b, 0) / past.length
  } catch {
    /* ignore */
  }
  return DEFAULT_SECONDS[mode] ?? 15
}

function fmt(seconds: number): string {
  const s = Math.max(0, Math.round(seconds))
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`
}

type Props = { mode: string; message: string; done: number; total: number; startedAt: number }

export function ProgressBar({ mode, message, done, total, startedAt }: Props) {
  const [now, setNow] = useState(Date.now())
  const [guess] = useState(() => typicalSeconds(mode))
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(t)
  }, [])

  const elapsed = (now - startedAt) / 1000
  const stepped = total > 1

  let pct: number
  let eta: number | null
  let late = false
  if (stepped) {
    pct = Math.min(100, Math.round((done / total) * 100))
    // Remaining time extrapolated from the average time per completed step.
    eta = done > 0 ? (elapsed / done) * (total - done) : null
  } else {
    // One model call: estimate from past runs; never show 100% before it actually finishes.
    pct = Math.min(95, Math.round((elapsed / guess) * 100))
    late = elapsed > guess
    eta = late ? null : guess - elapsed
  }

  return (
    <div className="progress-block">
      <div className="bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
        <div className="bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="progress-meta">
        <span className="progress-msg">{message}</span>
        <span>
          {pct}% · {fmt(elapsed)} elapsed
          {eta !== null && ` · ~${fmt(eta)} left`}
          {late && ' · taking longer than usual'}
        </span>
      </div>
    </div>
  )
}
