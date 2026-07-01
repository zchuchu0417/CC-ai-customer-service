import { useState, useEffect, useRef } from 'react'
import { useStreamChat } from './hooks/useStreamChat'
import { createSession, listSessions } from './api'
import MessageBubble from './components/MessageBubble'
import ChatInput from './components/ChatInput'

interface SessionItem {
  id: number
  user_id: number
  title: string
  status: string
}

export default function App() {
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [loading, setLoading] = useState(true)
  const { turns, isStreaming, sendMessage, setTurns } = useStreamChat(sessionId ?? 0)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 自动滚到最底
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])

  // 首次加载：拉会话列表，没有就建一个
  useEffect(() => {
    (async () => {
      try {
        const res = await listSessions(1)
        if (res.items && res.items.length > 0) {
          setSessions(res.items)
          setSessionId(res.items[0].id)
        } else {
          const s = await createSession(1, '我的会话')
          setSessions([s])
          setSessionId(s.id)
        }
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const handleNewSession = async () => {
    try {
      const s = await createSession(1, '新对话')
      setSessions((prev) => [s, ...prev])
      setSessionId(s.id)
      setTurns([])
    } catch (e) {
      console.error(e)
    }
  }

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center text-slate-500">
        加载中...
      </div>
    )
  }

  return (
    <div className="h-screen flex">
      {/* 左侧 · 会话列表 */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-4 border-b border-slate-200">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 bg-primary-700 text-white rounded-lg flex items-center justify-center text-sm font-bold">
              CC
            </div>
            <div>
              <div className="font-bold text-sm">CC 商城 AI 客服</div>
              <div className="text-xs text-slate-500">v1.0 · MVP</div>
            </div>
          </div>
          <button
            onClick={handleNewSession}
            className="w-full bg-primary-700 hover:bg-primary-900 text-white rounded-lg py-2 text-sm font-semibold transition"
          >
            + 新对话
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          <div className="text-xs text-slate-400 px-2 py-1 font-semibold">最近会话</div>
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => {
                setSessionId(s.id)
                setTurns([])
              }}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                sessionId === s.id
                  ? 'bg-primary-50 border border-primary-200 text-primary-900 font-semibold'
                  : 'hover:bg-slate-100 text-slate-700'
              }`}
            >
              <div className="truncate">{s.title}</div>
              <div className="text-xs text-slate-400 mt-0.5">#{s.id} · {s.status}</div>
            </button>
          ))}
        </div>

        <div className="p-3 border-t border-slate-200 text-xs text-slate-500">
          👤 测试用户 1
        </div>
      </aside>

      {/* 右侧 · 对话区 */}
      <main className="flex-1 flex flex-col">
        {/* 顶部 */}
        <header className="bg-white border-b border-slate-200 px-6 py-3 flex justify-between items-center">
          <div>
            <h1 className="font-bold">
              {sessions.find((s) => s.id === sessionId)?.title || '新对话'}
            </h1>
            <div className="text-xs text-slate-500">
              session #{sessionId} · RAG + Agent + 流式
            </div>
          </div>
          <div className="text-xs text-slate-400 flex gap-3">
            <span>📚 知识库 101 chunks</span>
            <span>🛠 3 个工具</span>
            <span>🎭 情绪感知</span>
          </div>
        </header>

        {/* 消息区 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {turns.length === 0 && (
            <div className="text-center text-slate-400 mt-20">
              <div className="text-4xl mb-3">👋</div>
              <div className="text-lg font-semibold">你好，我是 CC 商城 AI 客服</div>
              <div className="text-sm mt-2">问我退换货、物流、优惠券、商品参数...</div>
              <div className="text-xs mt-1 opacity-60">点击下方快捷问题即可测试</div>
            </div>
          )}

          {turns.map((t) => (
            <MessageBubble key={t.id} turn={t} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区 */}
        <ChatInput onSend={sendMessage} disabled={isStreaming || sessionId === null} />
      </main>
    </div>
  )
}
