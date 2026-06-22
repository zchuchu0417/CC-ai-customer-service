# 数据库 Schema 设计 v1.0

> 适用于 MVP 阶段（W2-W4）。RAG 知识库相关表（knowledge_docs / doc_chunks）在 W3 加入。

## 表清单

| 表名 | 用途 | 数据量级（预估） |
|---|---|---|
| users | 用户信息 | < 1 万 |
| sessions | 对话会话 | 10 万/月 |
| messages | 对话消息 | 100 万/月 |
| feedback | 用户反馈 | 30 万/月（30% 用户给反馈） |

## 表设计

### users · 用户表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK auto_increment | 主键 |
| external_id | VARCHAR(64) nullable | 关联电商系统的用户 ID |
| name | VARCHAR(64) nullable | 用户昵称 |
| role | ENUM('customer','admin') | 角色 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### sessions · 会话表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | 主键 |
| user_id | BIGINT FK→users.id | 所属用户 |
| title | VARCHAR(128) | 会话标题（首条消息自动摘要） |
| status | ENUM('active','closed','escalated') | 状态 |
| emotion_label | VARCHAR(32) nullable | 情绪标签（neutral/anger/sad） |
| created_at | DATETIME | 创建时间 |
| last_message_at | DATETIME nullable | 最后一条消息时间（排序用） |

### messages · 消息表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | 主键 |
| session_id | BIGINT FK→sessions.id | 所属会话 |
| role | ENUM('user','assistant','system') | 角色 |
| content | TEXT | 消息内容 |
| citations | JSON nullable | 引用列表 `[{title, source, score, page}]` |
| token_count | INT nullable | Token 消耗 |
| model_name | VARCHAR(32) nullable | 使用的模型名（如 deepseek-chat） |
| latency_ms | INT nullable | 响应耗时（毫秒） |
| created_at | DATETIME | 创建时间 |

### feedback · 反馈表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | 主键 |
| message_id | BIGINT FK→messages.id UNIQUE | 关联消息 |
| type | ENUM('like','dislike') | 类型 |
| reason | VARCHAR(32) nullable | 原因标签（答非所问/信息错误/没有引用/其他）|
| comment | VARCHAR(255) nullable | 用户补充评论 |
| created_at | DATETIME | 创建时间 |

## 索引设计

- `sessions(user_id, last_message_at DESC)` —— 查用户会话列表（最近优先）
- `messages(session_id, created_at)` —— 查会话内消息（时间顺序）
- `feedback(message_id)` —— UNIQUE，一条消息最多一个反馈

## 关系约束

- 删除 user 时，cascade 删除其 sessions（用户注销场景）
- 删除 session 时，cascade 删除其 messages 和对应 feedback
- 软删除暂不考虑，MVP 用硬删除

## ER图
┌──────────────────────┐
│       users          │
├──────────────────────┤
│ id          PK       │◄──┐
│ external_id          │   │
│ name                 │   │
│ role (customer/admin)│   │
│ created_at           │   │
│ updated_at           │   │
└──────────────────────┘   │
                           │
                           │ 1
                           │
                           │ N
                           │
┌──────────────────────┐   │
│      sessions        │   │
├──────────────────────┤   │
│ id          PK       │◄──┼──┐
│ user_id     FK ──────┼───┘  │
│ title                │      │
│ status (active/      │      │
│         closed/      │      │
│         escalated)   │      │
│ emotion_label        │      │
│ created_at           │      │
│ last_message_at      │      │
└──────────────────────┘      │
                              │ 1
                              │
                              │ N
                              │
┌──────────────────────┐      │
│      messages        │      │
├──────────────────────┤      │
│ id          PK       │◄──┐  │
│ session_id  FK ──────┼───┼──┘
│ role (user/          │   │
│       assistant)     │   │
│ content     TEXT     │   │
│ citations   JSON     │   │
│ token_count          │   │
│ model_name           │   │
│ latency_ms           │   │
│ created_at           │   │
└──────────────────────┘   │
                           │ 1
                           │
                           │ N (一条消息可能有 0-1 个反馈)
                           │
┌──────────────────────┐   │
│      feedback        │   │
├──────────────────────┤   │
│ id          PK       │   │
│ message_id  FK ──────┼───┘
│ type (like/dislike)  │
│ reason               │
│ comment              │
│ created_at           │
└──────────────────────┘