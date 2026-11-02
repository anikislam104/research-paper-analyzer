import { useEffect, useState } from 'react'
import Markdown from 'react-markdown'
import { cancelJob, getJob, getModes, startAnalysis, uploadPaper, type Mode, type PaperInfo, type Result } from './api'
import { download, toCsv, toMarkdown } from './export'
import { Diagram } from './Diagram'
import { ProgressBar, recordDuration } from './ProgressBar'
import './App.css'

const DESCRIPTIONS: Record<string, string> = {
  summary: 'A concise overview of the whole paper',
  sections: 'A short summary of each section',
  oneline: 'The paper in a single sentence',
  diagram: 'A flowchart of the method',
  slides: 'A slide deck you can download as .pptx',
  scope: 'The problem, its scope and the contributions',
  results: 'Key numbers and how they compare',
  dataset: 'Datasets used, sizes and splits',
  limitations: 'What the authors admit, and what may be missing',
}

function ResultView({ result, onSvg }: { result: Result; onSvg: (svg: string) => void }) {
  switch (result.type) {
    case 'table':
      return result.rows.length === 0 ? (
        <p>Nothing found in the paper.</p>
      ) : (
        <table>
          <thead>
            <tr>
              {result.columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row, i) => (
              <tr key={i}>
                {result.columns.map((c) => (
                  <td key={c}>{row[c]}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )
    case 'limitations':
      return (
        <div>
          <h3>Stated by the authors</h3>
          {result.stated.length ? (
            <ul>{result.stated.map((s) => <li key={s}>{s}</li>)}</ul>
          ) : (
            <p>None explicitly stated.</p>
          )}
          <h3>Inferred (model's own assessment)</h3>
          <ul>{result.inferred.map((s) => <li key={s}>{s}</li>)}</ul>
        </div>
      )
    case 'diagram':
      return <Diagram code={result.mermaid} onSvg={onSvg} />
    case 'slides':
      return (
        <div className="slides">
          {result.slides.map((s, i) => (
            <div className="slide" key={i}>
              <h3>{s.title}</h3>
              <ul>{s.bullets.map((b) => <li key={b}>{b}</li>)}</ul>
            </div>
          ))}
        </div>
      )
    case 'markdown':
      return <div className="prose"><Markdown>{result.content}</Markdown></div>
    case 'sections':
      return (
        <div>
          {result.items.map((i) => (
            <details key={i.section} open>
              <summary>{i.section}</summary>
              <p>{i.summary}</p>
            </details>
          ))}
        </div>
      )
    case 'scope':
      return (
        <div>
          <h3>Problem</h3>
          <p>{result.problem}</p>
          <h3>Scope</h3>
          <p>{result.scope}</p>
          <h3>Contributions</h3>
          <ul>
            {result.contributions.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      )
  }
}

export default function App() {
  const [paper, setPaper] = useState<PaperInfo | null>(null)
  const [modes, setModes] = useState<Mode[]>([])
  const [mode, setMode] = useState('')
  const [result, setResult] = useState<Result | null>(null)
  const [progress, setProgress] = useState({ message: '', done: 0, total: 0 })
  const [startedAt, setStartedAt] = useState(0)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [running, setRunning] = useState(false)
  const [jobId, setJobId] = useState('')
  const [svg, setSvg] = useState('')
  const [copied, setCopied] = useState(false)

  function copy() {
    if (!result) return
    navigator.clipboard.writeText(toMarkdown(result))
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  useEffect(() => {
    getModes().then(setModes).catch((e) => setError(e.message))
  }, [])

  async function handleFile(file: File | undefined) {
    if (!file) return
    setError('')
    setResult(null)
    setUploading(true)
    try {
      setPaper(await uploadPaper(file))
    } catch (e) {
      setPaper(null)
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  async function analyze() {
    if (!paper || !mode) return
    setError('')
    setResult(null)
    setSvg('')
    setRunning(true)
    const startedAtMs = Date.now()
    setStartedAt(startedAtMs)
    setProgress({ message: 'Starting', done: 0, total: 0 })
    try {
      const jobId = await startAnalysis(paper.paper_id, mode)
      setJobId(jobId)
      for (;;) {
        const job = await getJob(jobId)
        setProgress({ message: job.progress, done: job.done, total: job.total })
        if (job.status === 'done') {
          if (job.total <= 1) recordDuration(mode, (Date.now() - startedAtMs) / 1000)
          setResult(job.result)
          break
        }
        if (job.status === 'cancelled') break
        if (job.status === 'error') throw new Error(job.error ?? 'Analysis failed')
        await new Promise((r) => setTimeout(r, 1000))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed')
    } finally {
      setRunning(false)
    }
  }

  return (
    <main className="app">
      <header className="header">
        <img className="logo" src="/favicon.svg" alt="" width="44" height="44" />
        <div>
          <h1>Paper Analyzer</h1>
          <p className="tagline">Upload a research paper and get the part you need. Runs locally, nothing is stored.</p>
        </div>
      </header>

      <label
        className={paper ? 'dropzone has-file' : 'dropzone'}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          handleFile(e.dataTransfer.files[0])
        }}
      >
        <input type="file" accept="application/pdf" hidden onChange={(e) => handleFile(e.target.files?.[0])} />
        {uploading ? (
          <span className="drop-title">Reading PDF…</span>
        ) : paper ? (
          <>
            <span className="drop-title">{paper.title}</span>
            <span className="drop-hint">
              {paper.page_count} {paper.page_count === 1 ? 'page' : 'pages'} · {paper.char_count.toLocaleString()} characters · click to replace
            </span>
          </>
        ) : (
          <>
            <span className="drop-title">Drop a PDF here, or click to choose</span>
            <span className="drop-hint">Text-based PDFs up to 20 MB</span>
          </>
        )}
      </label>

      {paper && (
        <section className="panel">
          <h2>What would you like?</h2>
          <div className="modes">
            {modes.map((m) => (
              <button
                key={m.id}
                className={m.id === mode ? 'mode selected' : 'mode'}
                disabled={!m.available || running}
                title={m.available ? '' : 'Coming soon'}
                onClick={() => setMode(m.id)}
              >
                <span className="mode-label">{m.label}</span>
                <span className="mode-desc">{DESCRIPTIONS[m.id]}</span>
              </button>
            ))}
          </div>
          <div className="run-row">
            <button className="primary" disabled={!mode || running} onClick={analyze}>
              {running ? 'Analyzing…' : 'Analyze'}
            </button>
            {running && (
              <button className="ghost" onClick={() => cancelJob(jobId)}>
                Cancel
              </button>
            )}
          </div>
          {running && <ProgressBar mode={mode} {...progress} startedAt={startedAt} />}
        </section>
      )}

      {error && <p className="error">{error}</p>}

      {result && (
        <section className="panel result">
          <div className="result-head">
            <h2>{modes.find((m) => m.id === mode)?.label}</h2>
            <div className="actions">
              <button onClick={copy}>{copied ? 'Copied ✓' : 'Copy'}</button>
              <button onClick={() => download(`${mode}.md`, toMarkdown(result), 'text/markdown')}>.md</button>
              <button onClick={() => download(`${mode}.json`, JSON.stringify(result, null, 2), 'application/json')}>
                .json
              </button>
              {result.type === 'table' && (
                <button onClick={() => download(`${mode}.csv`, toCsv(result.columns, result.rows), 'text/csv')}>
                  .csv
                </button>
              )}
              {result.type === 'diagram' && (
                <>
                  <button disabled={!svg} onClick={() => download('diagram.svg', svg, 'image/svg+xml')}>
                    .svg
                  </button>
                  <button onClick={() => download('diagram.mmd', result.mermaid, 'text/plain')}>.mmd</button>
                </>
              )}
              {result.type === 'slides' && (
                <a className="button" href={`/api/jobs/${jobId}/pptx`} download>
                  .pptx
                </a>
              )}
            </div>
          </div>
          <ResultView result={result} onSvg={setSvg} />
        </section>
      )}
    </main>
  )
}
