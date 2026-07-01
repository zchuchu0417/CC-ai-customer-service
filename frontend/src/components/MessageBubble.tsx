import type { ChatTurn } from '../types'
import EmotionBadge from './EmotionBadge'
import ToolCallCard from './ToolCallCard'
import CitationCard from './CitationCard'

export default function MessageBubble({ turn }: { turn: ChatTurn }) {
  return (
    <div className="space-y-3">
      {/* 用户消息 */}
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-primary-700 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
          {turn.userText}
        </div>
      </div>

      {/* AI 区域（status + emotion + tool calls + answer + citations）*/}
      <div className="flex justify-start">
        <div className="max-w-[88%] w-full space-y-2">
          {/* AI 头像行 */}
          <div className="flex items-start gap-2">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-700 text-white text-xs font-bold flex items-center justify-center">
              AI
            </div>
            <div className="flex-1 space-y-2">
              {/* 状态文字 */}
              {turn.status && (
                <div className="text-xs text-slate-500 italic">{turn.status}</div>
              )}

              {/* 情绪标签 */}
              {turn.emotion && <EmotionBadge emotion={turn.emotion} />}

              {/* 工具调用卡片 */}
              {turn.toolCalls.map((tc, i) => (
                <ToolCallCard key={i} name={tc.name} args={tc.args} result={tc.result} />
              ))}

              {/* AI 回答正文 */}
              {(turn.aiText || turn.isStreaming) && (
                <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm whitespace-pre-wrap leading-relaxed">
                  <span>{turn.aiText}</span>
                  {turn.isStreaming && !turn.error && <span className="cursor-blink"></span>}
                </div>
              )}

              {/* 错误 */}
              {turn.error && (
                <div className="bg-red-50 border border-red-300 text-red-800 rounded-lg px-3 py-2 text-sm">
                  ❌ {turn.error}
                </div>
              )}

              {/* 引用卡片 */}
              {turn.citations.length > 0 && (
                <div className="space-y-2 mt-2">
                  <div className="text-xs text-slate-500 font-semibold">📚 引用资料</div>
                  {turn.citations.map((c) => (
                    <CitationCard key={c.index} citation={c} />
                  ))}
                </div>
              )}

              {/* 完成元信息 */}
              {turn.meta && (
                <div className="text-[10px] text-slate-400 mt-2">
                  ✅ {turn.meta.tokens} tokens · {turn.meta.latency_ms} ms · {turn.meta.model}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
