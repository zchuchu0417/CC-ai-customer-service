// 自定义 Hook：封装 SSE 流式对话
import { useState, useCallback } from 'react'
import type { ChatTurn } from '../types'

// 直接连后端，绕开 Vite proxy 缓冲问题
const API_BASE = 'http://localhost:8000/api/v1'

export function useStreamChat(sessionId: number) {
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [isStreaming, setIsStreaming] = useState(false)

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return

      const turnId = `turn_${Date.now()}`
      const newTurn: ChatTurn = {
        id: turnId,
        userText: text,
        status: '✓ 已发送',
        citations: [],
        toolCalls: [],
        aiText: '',
        isStreaming: true,
      }

      setTurns((prev) => [...prev, newTurn])
      setIsStreaming(true)

      // 更新当前 turn 的辅助函数
      const updateTurn = (patch: Partial<ChatTurn>) => {
        setTurns((prev) =>
          prev.map((t) => (t.id === turnId ? { ...t, ...patch } : t))
        )
      }
      const appendTurn = (patch: (prev: ChatTurn) => Partial<ChatTurn>) => {
        setTurns((prev) =>
          prev.map((t) => (t.id === turnId ? { ...t, ...patch(t) } : t))
        )
      }

      try {
        const resp = await fetch(
          `${API_BASE}/sessions/${sessionId}/messages/stream`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: text }),
          }
        )

        if (!resp.ok || !resp.body) {
          throw new Error(`HTTP ${resp.status}`)
        }

        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          const frames = buffer.split('\n\n')
          buffer = frames.pop() ?? ''

          for (const frame of frames) {
            if (!frame.trim()) continue
            let eventName = 'message'
            let dataStr = ''
            for (const line of frame.split('\n')) {
              if (line.startsWith('event:')) eventName = line.slice(6).trim()
              else if (line.startsWith('data:')) dataStr = line.slice(5).trim()
            }

            let data: any
            try {
              data = JSON.parse(dataStr)
            } catch {
              data = dataStr
            }

            switch (eventName) {
              case 'status':
                updateTurn({ status: data.message })
                break
              case 'emotion':
                updateTurn({ emotion: data })
                break
              case 'start':
                updateTurn({ citations: data.citations || [] })
                break
              case 'tool_call':
                appendTurn((t) => ({
                  toolCalls: [...t.toolCalls, { name: data.name, args: data.args }],
                }))
                break
              case 'tool_result':
                appendTurn((t) => ({
                  toolCalls: t.toolCalls.map((tc, i) =>
                    i === t.toolCalls.length - 1 ? { ...tc, result: data.result } : tc
                  ),
                }))
                break
              case 'token':
                appendTurn((t) => ({ aiText: t.aiText + (typeof data === 'string' ? data : '') }))
                break
              case 'done':
                updateTurn({ meta: data, isStreaming: false, status: '' })
                break
              case 'error':
                updateTurn({ error: data.message, isStreaming: false, status: '' })
                break
            }
          }
        }
      } catch (e: any) {
        updateTurn({ error: e.message || '请求失败', isStreaming: false })
      } finally {
        setIsStreaming(false)
      }
    },
    [sessionId, isStreaming]
  )

  return { turns, isStreaming, sendMessage, setTurns }
}
