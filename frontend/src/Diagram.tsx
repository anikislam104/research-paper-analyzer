import mermaid from 'mermaid'
import { useEffect, useRef, useState } from 'react'

mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' })

let counter = 0

export function Diagram({ code, onSvg }: { code: string; onSvg: (svg: string) => void }) {
  const ref = useRef<HTMLDivElement>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    mermaid
      .render(`mmd-${counter++}`, code)
      .then(({ svg }) => {
        if (cancelled || !ref.current) return
        ref.current.innerHTML = svg
        setError('')
        onSvg(svg)
      })
      .catch((e) => !cancelled && setError(String(e?.message ?? e)))
    return () => {
      cancelled = true
    }
  }, [code, onSvg])

  return (
    <>
      {error && <p className="error">Could not render diagram: {error}</p>}
      <div ref={ref} className="diagram" />
      <details>
        <summary>Mermaid source</summary>
        <pre>{code}</pre>
      </details>
    </>
  )
}
