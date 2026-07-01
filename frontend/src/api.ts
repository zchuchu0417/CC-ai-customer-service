// API 调用层
// 直接连后端，不走 Vite proxy（proxy 会缓冲 SSE 流，破坏流式效果）
// 后端已配置 CORS allow_origins=["*"]，安全无问题

const API_BASE = 'http://localhost:8000/api/v1'

export async function createSession(userId = 1, title?: string) {
  const resp = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, title }),
  })
  if (!resp.ok) throw new Error(`创建会话失败: ${resp.status}`)
  return resp.json()
}

export async function listSessions(userId = 1) {
  const resp = await fetch(`${API_BASE}/sessions?user_id=${userId}`)
  if (!resp.ok) throw new Error(`获取会话列表失败: ${resp.status}`)
  return resp.json()
}

export async function listMessages(sessionId: number) {
  const resp = await fetch(`${API_BASE}/sessions/${sessionId}/messages`)
  if (!resp.ok) throw new Error(`获取消息失败: ${resp.status}`)
  return resp.json()
}
