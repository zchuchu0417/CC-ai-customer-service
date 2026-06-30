# 🏗 CC 商城 AI 客服 · 系统架构文档

> 文档版本：v1.0
> 适用阶段：MVP（W1-W4）

---

## 1. 整体架构图（C4 - Level 1）

```mermaid
graph TB
    User[👤 用户<br/>Web/企业微信/飞书] -->|HTTPS + SSE| Gateway[API 网关<br/>FastAPI]

    Gateway --> Router[路由层<br/>/sessions /messages /health]
    Router --> Service[业务服务层<br/>message_service / session_service]

    Service --> RAG[RAG 检索服务<br/>rag_service.py]
    Service --> LLM[LLM 客户端<br/>llm_client.py + tools]
    Service --> Agent[Agent 工具体系<br/>agent_tools.py]
    Service --> Emotion[情绪检测<br/>emotion_detector.py]

    RAG --> Embed[Embedding 客户端<br/>bge-m3]
    RAG --> Rerank[Rerank 客户端<br/>bge-reranker-v2-m3]

    LLM -.OpenAI 协议.-> DeepSeek[(DeepSeek-V3 Pro<br/>SiliconFlow API)]
    Embed -.OpenAI 协议.-> SiliconFlow1[(SiliconFlow<br/>BAAI/bge-m3)]
    Rerank -.HTTP.-> SiliconFlow2[(SiliconFlow<br/>BAAI/bge-reranker-v2-m3)]

    Service --> MySQL[(MySQL 8.0<br/>users/sessions/messages<br/>feedback/knowledge_docs<br/>doc_chunks)]
    Service --> Redis[(Redis 7<br/>会话上下文缓存)]
    RAG --> Qdrant[(Qdrant 1.11<br/>101 chunks<br/>BAAI/bge-m3 1024 维)]

    Agent --> Tools[3 个 Mock 工具<br/>query_order<br/>create_return_request<br/>escalate_to_human]

    style User fill:#e3f2fd
    style Gateway fill:#fff3e0
    style RAG fill:#f3e5f5
    style LLM fill:#fff9c4
    style Agent fill:#ffebee
    style Emotion fill:#fce4ec
    style MySQL fill:#e8f5e9
    style Redis fill:#ffcdd2
    style Qdrant fill:#d1c4e9
    style DeepSeek fill:#ce93d8
    style SiliconFlow1 fill:#80cbc4
    style SiliconFlow2 fill:#80cbc4
```

---

## 2. 一次问答完整时序图

```mermaid
sequenceDiagram
    autonumber
    participant U as 👤 用户
    participant API as FastAPI
    participant MS as message_service
    participant ED as 情绪检测
    participant RAG as RAG 服务
    participant Qdrant as Qdrant 向量库
    participant LLM as DeepSeek-V3
    participant Tools as Agent 工具
    participant DB as MySQL

    U->>API: POST /sessions/1/messages/stream<br/>{"content":"订单 ORD20250603 到哪了?"}
    API->>MS: chat_stream(session_id, content)

    Note over MS: Step 1: 验证 session
    MS->>DB: 查 sessions 表
    DB-->>MS: session 存在 ✓

    Note over MS: Step 2: 保存用户消息
    MS->>DB: INSERT messages
    MS-->>U: 🟦 SSE event: status "✓ 收到问题"

    Note over MS: Step 2.5: 情绪检测
    MS->>ED: detect_emotion(content)
    ED-->>MS: {label:"neutral", intensity:0}

    Note over MS: Step 3: 招呼语检测
    Note right of MS: 含订单号 → 不是招呼语<br/>触发 forced_tool_choice<br/>= query_order

    MS-->>U: 🟦 SSE: status "🔍 检索知识库中..."

    Note over MS: Step 4: RAG 检索
    MS->>RAG: retrieve(content, top_k=5)
    RAG->>Qdrant: embedding + 向量检索
    Qdrant-->>RAG: 5 个 chunks
    RAG-->>MS: chunks (用于 prompt 上下文)
    MS-->>U: 🟦 SSE: status "📚 找到 5 条相关资料"
    MS-->>U: 🟦 SSE: event=start, citations=[...]

    Note over MS: Step 5: Agent 主循环（第 1 轮）
    MS-->>U: 🟦 SSE: status "🎯 检测到明确意图，强制调用工具"

    MS->>LLM: chat(messages + tools + tool_choice=query_order)
    LLM-->>MS: tool_calls=[query_order(ORD20250603)]
    MS-->>U: 🟦 SSE: event=tool_call

    MS->>Tools: execute_tool(query_order, ORD20250603)
    Tools-->>MS: {success:true, order:{...物流数据...}}
    MS-->>U: 🟦 SSE: event=tool_result

    Note over MS: Step 5: Agent 主循环（第 2 轮）
    MS->>LLM: chat(messages + tool result + tool_choice=auto)
    LLM-->>MS: 最终答案文本（不再调工具）

    loop 流式输出
        MS-->>U: 🟦 SSE: event=token, data="您"
        MS-->>U: 🟦 SSE: event=token, data="的"
        MS-->>U: 🟦 SSE: event=token, data="订"
        MS-->>U: 🟦 SSE: event=token, data="单"
    end

    Note over MS: Step 6: 保存 AI 消息
    MS->>DB: INSERT messages (含 citations, tokens, latency)
    MS->>DB: UPDATE sessions.last_message_at
    MS-->>U: 🟦 SSE: event=done
```

---

## 3. RAG 离线灌库流程

```mermaid
flowchart LR
    A[data/knowledge/<br/>15 篇 .md] --> B[parse markdown<br/>按 H2 切段]
    B --> C[chunk_markdown<br/>400 字 + 50 字重叠]
    C --> D[BAAI/bge-m3<br/>批量 embedding API]
    D --> E[1024 维向量 × 101 chunks]

    E --> F[(Qdrant<br/>cc_knowledge collection)]
    C --> G[(MySQL<br/>doc_chunks 元数据)]
    A --> H[(MySQL<br/>knowledge_docs 文档信息)]

    style A fill:#e3f2fd
    style F fill:#d1c4e9
    style G fill:#e8f5e9
    style H fill:#e8f5e9
```

---

## 4. Agent 决策树

```mermaid
flowchart TD
    Start([用户提问]) --> Intent{意图检测<br/>detect_forced_tool}

    Intent -->|含订单号 ORD\d+| ForceOrder[强制 tool_choice=query_order]
    Intent -->|退货+订单号| ForceRequired[强制 tool_choice=required]
    Intent -->|转人工关键词| ForceEscalate[强制 tool_choice=escalate_to_human]
    Intent -->|无明确意图| AutoMode[tool_choice=auto]

    ForceOrder --> LLM1[LLM 第 1 轮]
    ForceRequired --> LLM1
    ForceEscalate --> LLM1
    AutoMode --> LLM1

    LLM1 --> HasTool{有 tool_calls?}
    HasTool -->|否| Final[流式输出最终答案]
    HasTool -->|是| ExecTool[执行工具]
    ExecTool --> LLM2[LLM 第 2 轮<br/>tool_choice=auto]
    LLM2 --> HasTool2{还要调工具吗?}
    HasTool2 -->|否| Final
    HasTool2 -->|是, 第 3 轮| ExecTool
    HasTool2 -->|超过 4 轮| Stop[强制终止<br/>返回升级提示]

    style Start fill:#e3f2fd
    style Final fill:#c8e6c9
    style Stop fill:#ffcdd2
    style ForceOrder fill:#fff9c4
    style ForceRequired fill:#fff9c4
    style ForceEscalate fill:#fff9c4
```

---

## 5. 数据库 ER 图

```mermaid
erDiagram
    USERS ||--o{ SESSIONS : has
    SESSIONS ||--o{ MESSAGES : contains
    MESSAGES ||--o| FEEDBACK : may_have
    KNOWLEDGE_DOCS ||--o{ DOC_CHUNKS : split_into

    USERS {
        bigint id PK
        string external_id
        string name
        enum role "customer/admin"
        datetime created_at
    }

    SESSIONS {
        bigint id PK
        bigint user_id FK
        string title
        enum status "active/closed/escalated"
        string emotion_label
        datetime created_at
        datetime last_message_at
    }

    MESSAGES {
        bigint id PK
        bigint session_id FK
        enum role "user/assistant/system"
        text content
        json citations
        int token_count
        string model_name
        int latency_ms
        datetime created_at
    }

    FEEDBACK {
        bigint id PK
        bigint message_id FK,UQ
        enum type "like/dislike"
        string reason
        string comment
    }

    KNOWLEDGE_DOCS {
        bigint id PK
        string title
        string source_path
        string category
        int chunk_count
    }

    DOC_CHUNKS {
        bigint id PK
        bigint doc_id FK
        int chunk_index
        text content
        string section
        string vector_id "Qdrant point id"
    }
```

---

## 6. 部署架构（W1-W4 本地 + 未来生产建议）

### 当前（本地开发）

```
┌────────────────────────────────────────┐
│  开发者本机（Windows + Docker Desktop）│
│                                        │
│  ┌─────────────────────────────────┐   │
│  │ Python 进程（uvicorn）           │   │
│  │   FastAPI :8000                 │   │
│  └────────────┬────────────────────┘   │
│               │                        │
│  ┌────────────▼──────────────────────┐ │
│  │ Docker Compose                    │ │
│  │   - MySQL :13306                  │ │
│  │   - Redis :6379                   │ │
│  │   - Qdrant :6333                  │ │
│  │   - Adminer :8080                 │ │
│  └────────────────────────────────────┘ │
└────────────────────────────────────────┘
           │
           │ HTTPS
           ▼
  ┌────────────────┐
  │ 硅基流动 API     │
  │ DeepSeek API   │
  └────────────────┘
```

### 未来生产架构（V2 - 不在本项目范围）

- **Web 层**：Nginx 反向代理 + SSL + 限流
- **应用层**：3+ FastAPI 实例（K8s HPA 弹性扩缩）
- **缓存层**：Redis Cluster
- **数据层**：MySQL 主从读写分离
- **向量库**：Qdrant Cluster（3 节点）
- **可观测**：Prometheus + Grafana + Sentry
- **CI/CD**：GitHub Actions → 镜像仓库 → K8s 滚动更新

---

## 7. 关键设计决策

| 决策点 | 选 A | 选 B | 选 | 原因 |
|---|---|---|---|---|
| LLM 协议 | OpenAI Function Calling | LangChain Agent | **A** | 协议标准、跨厂商 |
| 向量库 | Milvus | Qdrant | **Qdrant** | CPU 友好，本地 Docker |
| 流式协议 | WebSocket | SSE | **SSE** | 单向流式更简单 |
| RAG 切分 | 固定长度 | 按 H2 标题 + 长度兜底 | **B** | 语义完整 |
| Rerank | 启用 | 暂不启用 | **暂不** | 65 题评测 100%，无收益 |
| 多供应商 | 锁定一家 | 分能力路由 | **分能力路由** | 防绑定 + 成本/性能最优 |
| Function call 控制 | tool_choice=auto | 检测意图 + 强制 | **强制** | 防 In-Context Learning Bias |

---

## 8. 已知 issues 与未来优化

| 编号 | 问题 | 影响 | 优先级 | 计划 |
|---|---|---|---|---|
| #01 | 首 Token 延迟 2-3s（免费 API 限制）| 用户体感 | 中 | V2 接入更快 LLM / 本地推理 |
| #02 | 知识库仅 100 chunks（mock 数据）| 演示用 | 低 | 生产环境对接真实知识库 |
| #03 | 无管理后台 | 运营难管控 | 中 | V2 加 React 管理 UI |
| #04 | 无前端正式 UI（仅测试 HTML）| 用户视角不全 | 中 | V2 React + Ant Design 完整页面 |
| #05 | 情绪检测仅关键词版 | 召回有限 | 低 | V3 升级 LLM 情绪分类 |
| #06 | 工具调用日志未入库 | 难复盘 | 低 | V2 加 tool_call_logs 表 |
