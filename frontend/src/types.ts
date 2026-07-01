// SSE 事件类型（与后端 message_service.chat_stream 对齐）

export type SSEEvent =
  | { event: 'status'; data: { stage: string; message: string } }
  | { event: 'emotion'; data: EmotionInfo }
  | { event: 'start'; data: { user_message_id: number; citations: Citation[] } }
  | { event: 'tool_call'; data: { name: string; args: Record<string, any> } }
  | { event: 'tool_result'; data: { name: string; result: any } }
  | { event: 'token'; data: string }
  | { event: 'done'; data: { assistant_message_id: number; tokens: number; latency_ms: number; model: string } }
  | { event: 'error'; data: { message: string } }

export interface EmotionInfo {
  label: 'anger' | 'disappointment' | 'anxiety' | 'complaint' | 'neutral'
  label_cn: string
  intensity: number
  matched_keywords: string[]
}

export interface Citation {
  index: number
  title: string
  section: string | null
  content_preview: string
  score: number
  doc_id: number
  category: string
}

export interface ChatTurn {
  id: string
  userText: string
  status: string                  // 当前状态文字
  emotion?: EmotionInfo
  citations: Citation[]
  toolCalls: { name: string; args: Record<string, any>; result?: any }[]
  aiText: string                  // 累积的流式答案
  meta?: { assistant_message_id: number; tokens: number; latency_ms: number; model: string }
  isStreaming: boolean
  error?: string
}
