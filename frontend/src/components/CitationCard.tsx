import type { Citation } from '../types'

export default function CitationCard({ citation }: { citation: Citation }) {
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs">
      <div className="font-semibold text-primary-900">
        【{citation.index}】{citation.title}
        {citation.section && <span className="text-slate-500 font-normal"> · {citation.section}</span>}
      </div>
      <div className="mt-1 text-slate-600 line-clamp-2">{citation.content_preview}</div>
      <div className="mt-1 text-slate-400">
        分数：{citation.score} · 分类：{citation.category}
      </div>
    </div>
  )
}
