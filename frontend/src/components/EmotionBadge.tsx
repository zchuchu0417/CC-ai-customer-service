import type { EmotionInfo } from '../types'

const ICONS: Record<string, string> = {
  anger: '😡',
  disappointment: '😔',
  anxiety: '😟',
  complaint: '⚠️',
  neutral: '🙂',
}

export default function EmotionBadge({ emotion }: { emotion: EmotionInfo }) {
  const { label, label_cn, intensity, matched_keywords } = emotion
  if (intensity < 4) return null

  const color =
    intensity >= 7
      ? 'bg-red-50 border-red-300 text-red-800'
      : 'bg-amber-50 border-amber-300 text-amber-800'

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold ${color}`}>
      <span className="text-base">{ICONS[label] ?? '🙂'}</span>
      <span>情绪：{label_cn} · 强度 {intensity}/10</span>
      {matched_keywords.length > 0 && (
        <span className="opacity-60 font-normal">· 触发：{matched_keywords.join('、')}</span>
      )}
    </div>
  )
}
