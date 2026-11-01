import { useEffect, useState } from 'react'
import Markdown from 'react-markdown'
import { cancelJob, getJob, getModes, startAnalysis, uploadPaper, type Mode, type PaperInfo, type Result } from './api'
import { download, toCsv, toMarkdown } from './export'
import { Diagram } from './Diagram'
import './App.css'

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
  const [progress, setProgress] = useState('')
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [running, setRunning] = useState(false)
  const [jobId, setJobId] = useState('')
  const [svg, setSvg] = useState('')

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
    setProgress('Starting')
    try {
      const jobId = await startAnalysis(paper.paper_id, mode)
      setJobId(jobId)
      for (;;) {
        const job = await getJob(jobId)
        setProgress(job.progress)
        if (job.status === 'done') {
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
      <h1>Paper Analyzer</h1>
      <label
        className="dropzone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          handleFile(e.dataTransfer.files[0])
        }}
      >
        <input type="file" accept="application/pdf" hidden onChange={(e) => handleFile(e.target.files?.[0])} />
        {uploading
          ? 'Reading PDF…'
          : paper
            ? `${paper.title} — ${paper.page_count} pages (click to replace)`
            : 'Drop a PDF here or click to choose'}
      </label>

      {paper && (
        <>
          <div className="modes">
            {modes.map((m) => (
              <button
                key={m.id}
                className={m.id === mode ? 'mode selected' : 'mode'}
                disabled={!m.available || running}
                title={m.available ? '' : 'Coming soon'}
                onClick={() => setMode(m.id)}
              >
                {m.label}
              </button>
            ))}
          </div>
          <button className="analyze" disabled={!mode || running} onClick={analyze}>
            {running ? 'Analyzing…' : 'Analyze'}
          </button>
          {running && (
            <p className="progress">
              {progress} <button onClick={() => cancelJob(jobId)}>Cancel</button>
            </p>
          )}
        </>
      )}

      {error && <p className="error">{error}</p>}

      {result && (
        <section className="result">
          <div className="actions">
            <button onClick={() => navigator.clipboard.writeText(toMarkdown(result))}>Copy</button>
            <button onClick={() => download(`${mode}.md`, toMarkdown(result), 'text/markdown')}>Download .md</button>
            <button onClick={() => download(`${mode}.json`, JSON.stringify(result, null, 2), 'application/json')}>
              Download .json
            </button>
            {result.type === 'table' && (
              <button onClick={() => download(`${mode}.csv`, toCsv(result.columns, result.rows), 'text/csv')}>
                Download .csv
              </button>
            )}
            {result.type === 'diagram' && (
              <>
                <button disabled={!svg} onClick={() => download('diagram.svg', svg, 'image/svg+xml')}>Download .svg</button>
                <button onClick={() => download('diagram.mmd', result.mermaid, 'text/plain')}>Download .mmd</button>
              </>
            )}
            {result.type === 'slides' && (
              <a className="button" href={`/api/jobs/${jobId}/pptx`} download>
                Download .pptx
              </a>
            )}
          </div>
          <ResultView result={result} onSvg={setSvg} />
        </section>
      )}
    </main>
  )
}
