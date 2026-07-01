import { useState, KeyboardEvent } from 'react'

interface Props {
  onSend: (text: string) => void
  disabled: boolean
}

const QUICK_PROMPTS = [
  '鞋子可以 7 天无理由退货吗？',
  '帮我查一下订单 ORD20250603',
  '你们家电视机怎么调白平衡？',
  '你这个机器人不懂事！我要转人工！',
]

export default function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState('')

  const handleSend = () => {
    if (!text.trim() || disabled) return
    onSend(text)
    setText('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-slate-200 bg-white p-4 space-y-3">
      {/* 快捷问题 */}
      <div className="flex flex-wrap gap-2">
        {QUICK_PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => !disabled && onSend(p)}
            disabled={disabled}
            className="text-xs px-3 py-1.5 rounded-full bg-slate-100 hover:bg-slate-200 disabled:opacity-50 transition"
          >
            {p}
          </button>
        ))}
      </div>

      {/* 输入框 */}
      <div className="flex gap-2 items-end">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入问题... Shift+Enter 换行"
          disabled={disabled}
          rows={2}
          className="flex-1 resize-none border border-slate-300 rounded-xl px-4 py-3 focus:border-primary-500 focus:outline-none disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          className="px-6 py-3 bg-primary-700 hover:bg-primary-900 disabled:bg-slate-300 text-white rounded-xl font-semibold transition"
        >
          {disabled ? '思考中...' : '发送'}
        </button>
      </div>
    </div>
  )
}
