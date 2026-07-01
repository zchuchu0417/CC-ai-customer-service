interface Props {
  name: string
  args: Record<string, any>
  result?: any
}

export default function ToolCallCard({ name, args, result }: Props) {
  return (
    <div className="space-y-2 my-2">
      {/* 调用框（黄色）*/}
      <div className="bg-amber-50 border border-amber-300 rounded-lg p-3">
        <div className="text-amber-900 font-semibold text-xs flex items-center gap-2">
          🔧 调用 <code className="font-mono">{name}(...)</code>
        </div>
        <pre className="mt-2 text-xs text-slate-700 font-mono whitespace-pre-wrap overflow-x-auto">
          {JSON.stringify(args, null, 2)}
        </pre>
      </div>

      {/* 结果框（绿色）*/}
      {result && (
        <div className="bg-emerald-50 border border-emerald-300 rounded-lg p-3">
          <div className="text-emerald-900 font-semibold text-xs">
            ✅ {name} 返回：
          </div>
          <pre className="mt-2 text-xs text-emerald-900 font-mono whitespace-pre-wrap overflow-x-auto max-h-64 overflow-y-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
