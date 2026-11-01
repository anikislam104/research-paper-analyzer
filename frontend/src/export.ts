import type { Result } from './api'

export function toMarkdown(r: Result): string {
  switch (r.type) {
    case 'markdown':
      return r.content
    case 'sections':
      return r.items.map((i) => `## ${i.section}\n\n${i.summary}`).join('\n\n')
    case 'scope':
      return [
        `## Problem\n\n${r.problem}`,
        `## Scope\n\n${r.scope}`,
        `## Contributions\n\n${r.contributions.map((c) => `- ${c}`).join('\n')}`,
      ].join('\n\n')
    case 'table': {
      const esc = (v: unknown) => String(v ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ')
      return [
        `| ${r.columns.join(' | ')} |`,
        `| ${r.columns.map(() => '---').join(' | ')} |`,
        ...r.rows.map((row) => `| ${r.columns.map((c) => esc(row[c])).join(' | ')} |`),
      ].join('\n')
    }
    case 'limitations':
      return [
        `## Stated by the authors\n\n${r.stated.map((s) => `- ${s}`).join('\n') || '_None stated_'}`,
        `## Inferred (not stated by the authors)\n\n${r.inferred.map((s) => `- ${s}`).join('\n')}`,
      ].join('\n\n')
    case 'diagram':
      return '```mermaid\n' + r.mermaid + '\n```'
    case 'slides':
      return r.slides.map((s, i) => `## ${i + 1}. ${s.title}\n\n${s.bullets.map((b) => `- ${b}`).join('\n')}`).join('\n\n')
  }
}

export function toCsv(columns: string[], rows: Record<string, string>[]): string {
  const q = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`
  return [columns.map(q).join(','), ...rows.map((row) => columns.map((c) => q(row[c])).join(','))].join('\r\n')
}

export function download(filename: string, content: string, mime: string) {
  const url = URL.createObjectURL(new Blob([content], { type: mime }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
