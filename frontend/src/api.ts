export type PaperInfo = {
  paper_id: string
  title: string
  page_count: number
  char_count: number
  preview: string
}

export type Mode = { id: string; label: string; available: boolean }

export type Result =
  | { type: 'markdown'; content: string }
  | { type: 'sections'; items: { section: string; summary: string }[] }
  | { type: 'scope'; problem: string; scope: string; contributions: string[] }
  | { type: 'table'; columns: string[]; rows: Record<string, string>[] }
  | { type: 'limitations'; stated: string[]; inferred: string[] }
  | { type: 'diagram'; mermaid: string }
  | { type: 'slides'; title: string; slides: { title: string; bullets: string[] }[] }

export type Job = {
  id: string
  mode: string
  status: 'running' | 'done' | 'error' | 'cancelled'
  progress: string
  result: Result | null
  error: string | null
}

async function fail(res: Response, fallback: string): Promise<never> {
  const body = await res.json().catch(() => null)
  throw new Error(body?.detail ?? `${fallback} (${res.status})`)
}

export async function uploadPaper(file: File): Promise<PaperInfo> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/papers', { method: 'POST', body: form })
  if (!res.ok) await fail(res, 'Upload failed')
  return res.json()
}

export async function getModes(): Promise<Mode[]> {
  const res = await fetch('/api/modes')
  if (!res.ok) await fail(res, 'Could not load modes')
  return res.json()
}

export async function startAnalysis(paperId: string, mode: string): Promise<string> {
  const res = await fetch(`/api/papers/${paperId}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  })
  if (!res.ok) await fail(res, 'Could not start analysis')
  return (await res.json()).job_id
}

export async function cancelJob(jobId: string): Promise<void> {
  await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' })
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`/api/jobs/${jobId}`)
  if (!res.ok) await fail(res, 'Could not read job')
  return res.json()
}
