# CC 商城 AI 客服 · React 前端

> Vite + React 18 + TypeScript + Tailwind CSS
>
> 简化版正式前端，对接后端 SSE 流式接口

## ✨ 功能

- 💬 完整对话界面（左侧会话列表 + 右侧消息流）
- 📡 SSE 流式输出（打字机效果 + 状态反馈）
- 🎭 情绪标签可视化（愤怒 / 失望 / 焦虑 / 投诉）
- 🔧 Agent 工具调用展示（黄框调用 + 绿框返回）
- 📚 引用卡片（每条 RAG 检索结果可视化）
- ⚡ 快捷问题按钮（一键测试 4 种场景）

## 🚀 启动

### 1. 确认后端已启动

后端 uvicorn 必须在 `http://localhost:8000` 运行（前端通过 Vite proxy 转发 `/api` 请求过去）。

### 2. 安装依赖

```bash
cd frontend
npm install
```

首次安装需要 1-2 分钟。

### 3. 启动开发服务器

```bash
npm run dev
```

浏览器会自动打开 http://localhost:5173

## 🎬 推荐测试顺序

按以下顺序点快捷问题，能完整 demo 项目所有能力：

1. **`鞋子可以 7 天无理由退货吗？`** → 标准 RAG 问答 + 引用
2. **`帮我查一下订单 ORD20250603`** → Agent 调 query_order 工具
3. **`你们家电视机怎么调白平衡？`** → AI 主动承认无知（最值钱）
4. **`你这个机器人不懂事！我要转人工！`** → 情绪感知 + 自动转人工

## 📂 项目结构

```
frontend/
├── index.html                 # HTML 入口
├── package.json
├── vite.config.ts             # Vite 配置（含 /api proxy）
├── tailwind.config.js
└── src/
    ├── main.tsx               # React 挂载
    ├── App.tsx                # 主页面（左会话列表 + 右对话区）
    ├── index.css              # 全局样式 + Tailwind
    ├── types.ts               # TypeScript 类型定义
    ├── api.ts                 # REST API 调用
    ├── hooks/
    │   └── useStreamChat.ts   # 自定义 Hook：SSE 流式对话核心逻辑
    └── components/
        ├── MessageBubble.tsx  # 单条消息气泡（用户 + AI）
        ├── ChatInput.tsx      # 输入框 + 快捷问题
        ├── EmotionBadge.tsx   # 情绪标签
        ├── ToolCallCard.tsx   # 工具调用黄绿框
        └── CitationCard.tsx   # 引用卡片
```

## 🛠 开发说明

- **proxy 配置**：`vite.config.ts` 已配置 `/api` → `http://localhost:8000`，无需 CORS 担心
- **SSE 解析**：`useStreamChat.ts` 用 `ReadableStream` 读取 SSE 流，按 `event:` / `data:` 解析
- **状态管理**：纯 `useState`，无 Redux/Zustand（项目小，过度设计反而拖慢）
- **样式**：纯 Tailwind utility classes，没有自定义 CSS 框架

## 🚧 已知 limitations

- 未做用户登录（写死 user_id=1）
- 未做消息历史持久化加载（刷新页面会清空对话，但 MySQL 里已保留）
- 未做错误重试机制
- 未做移动端适配（仅桌面 ≥ 1024px）

这些都是 V2 待办，MVP 阶段不影响 demo。

## 📦 生产构建

```bash
npm run build
```

输出到 `dist/` 目录，可部署到 Vercel / Netlify / GitHub Pages（需配置后端 API 公网地址）。
