<div align="center">

# 🛒 CC 商城 AI 客服助手

**企业级 AI 智能问答系统 · RAG + Agent + 情绪感知 · 全栈端到端**

由 AI 产品经理从 0 到 1 设计、实施、评测、上线

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/status-MVP%20Ready-brightgreen)]()
[![Stage](https://img.shields.io/badge/stage-W4%20Polishing-blue)]()
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)]()
[![DeepSeek-V3](https://img.shields.io/badge/LLM-DeepSeek--V3-purple.svg)]()

[📄 PRD 文档](./docs/PRD_v1.md) ·
[📊 评测报告](./docs/rag_evaluation_report.md) ·
[🎨 UI 原型](./mockups/README.md) ·
[🗄 数据库设计](./docs/db_schema.md)

</div>

---

## ✨ 一句话项目定义

**面向电商 C 端用户的智能问答系统**：通过 **RAG**（检索增强生成）给出带原文出处的回答，通过 **Agent** 工具调用真实查询订单、创建退货单、转接人工客服，通过**情绪感知**对负面情绪用户先共情再解决。

> 这不是 ChatGPT 套壳 —— **每个回答都有引用、每个动作都有真实数据支撑**。

---

## 🎯 解决什么问题

据艾瑞咨询 2024 年报告，电商客服日均咨询量中 **65% 为重复性问题**，但人工平均响应 **3-5 分钟**，旺季高峰 30 分钟以上。

| 指标 | 行业现状 | 本项目目标 | 当前评测 |
|---|---|---|---|
| 单次问答自助解决率（北极星）| ~40% | ≥ 70% | 待生产验证 |
| 答案采纳率 | ~50% | ≥ 75% | 待生产验证 |
| RAG 召回率（Recall@5）| - | ≥ 90% | **100%**（65 题评测集）✅ |
| MRR（平均倒数排名）| - | ≥ 0.85 | **0.9569** ✅ |
| 首 Token 响应 | - | ≤ 3 秒 | ~2 秒（Pro API） |
| 工具调用成功率 | - | ≥ 90% | **95%+**（修复 ICL Bias 后）✅ |

---

## 🏗 系统架构

```
                        ┌─────────────────────────────────────┐
                        │     用户（Web / 企业微信 / 飞书）       │
                        └──────────────┬──────────────────────┘
                                       │ HTTPS / SSE 长连接
                        ┌──────────────▼──────────────────────┐
                        │  FastAPI 后端（流式 + 三层架构）        │
                        └──┬──────────┬──────────┬─────────────┘
                           │          │          │
                  ┌────────┘   ┌──────┘   ┌──────┘
                  │            │          │
              ┌───▼───┐    ┌───▼──────┐ ┌─▼──────────────┐
              │ MySQL │    │  Redis   │ │ Qdrant 向量库   │
              │会话/消息│   │ 会话缓存 │ │ 101 chunks     │
              └───────┘    └──────────┘ └────────────────┘
                                            ▲
                  ┌─────────────────────────┴──────────────┐
                  │  RAG 检索（bge-m3）+ Rerank 评测        │
                  └────────────────────────────────────────┘

                  ┌────────────────────────────────────────┐
                  │  LLM (DeepSeek-V3 Pro) - OpenAI 兼容    │
                  │  + Function Calling                    │
                  │  + 3 个 Agent 工具                      │
                  └────────────────────────────────────────┘
```

📌 详细架构图见 [docs/architecture.md](./docs/architecture.md)

---

## 🚀 核心能力

### 1️⃣ RAG 带引用回答

```
👤 用户：鞋子可以 7 天无理由退货吗？
🤖 AI（基于 RAG 检索）：
   根据《CC 商城 7 天无理由退货政策》，鞋子可以申请，需满足 3 个条件：
   1. 商品未影响二次销售（未拆封、标签完好）【1】
   2. 商品未实际使用（未穿着、未洗涤）【1】
   3. 保留原包装、吊牌、说明书【1】

   📚 引用：CC 商城 7 天无理由退货政策 · 一、适用条件（相似度 0.83）
```

### 2️⃣ Agent 工具调用（真实数据）

```
👤 用户：帮我查一下订单 ORD20250603 现在到哪了？
🤖 AI：🎯 检测到订单号 → 强制调用 query_order

   🔧 调用 query_order({"order_id": "ORD20250603"})
   ✅ 返回：{"status": "shipped", "logistics": {"carrier": "顺丰速运",
            "current_location": "上海浦东中转站", ...}}

   您的订单 ORD20250603 物流状态：
   - 物流公司：顺丰速运
   - 运单号：SF1234567890
   - 当前位置：上海浦东中转站
   - 预计送达：2026 年 6 月 25 日 18:00 前
```

### 3️⃣ 拒答 + 主动承认无知

```
👤 用户：你们家的电视机怎么调白平衡？
🤖 AI：
   抱歉，这个问题我没有找到准确依据，建议您联系人工客服。

   目前我们的参考资料仅包含 CC Pods Pro 耳机 和 CC Run X1 运动跑鞋
   的相关信息。没有电视机的产品说明或设置指南。
```

> ⭐ 这是 RAG 最值钱的能力 —— **知道自己不知道什么**，比啥都能答的"瞎编大师"强 100 倍。

### 4️⃣ 情绪感知共情

```
👤 用户：你这个机器人不懂事！我要转人工！
🎭 情绪检测：愤怒（强度 8/10）→ 自动升级 session 状态为 escalated
🤖 AI（先共情）：
   非常抱歉给您带来不好的体验，完全理解您的感受 🙏

   🔧 调用 escalate_to_human({"reason": "用户要求转人工", "urgency": "high"})
   ✅ 返回：{"ticket_id": "TKT20260629...", "queue_position": 1,
            "estimated_wait": "1-2 分钟"}

   已为您接入人工客服，工单号 TKT20260629...，预计 1-2 分钟内有客服跟您联系。
```

### 5️⃣ 流式输出（SSE）

打字机效果 + 全程进度反馈（"✓ 收到问题"→"🔍 检索知识库"→"🤖 AI 正在思考"），用户从 0ms 就有反馈。

---

## 📊 评测体系（业内罕见）

详见 [📊 RAG 评测对比报告](./docs/rag_evaluation_report.md)

### 评测集
- **50 条标准评测**（覆盖 11 类业务）+ **15 条 Hard Cases**（口语化/错别字/跨文档）
- 每条人工标注 ground truth `expected_doc_ids`
- 自动化指标：Recall@K / MRR / 平均延迟 / 分类细分

### 实验对比

| 方案 | Recall@5 | MRR | 延迟 | API 成本 |
|---|---:|---:|---:|---:|
| **v1 纯向量**（bge-m3 + Qdrant）| **100%** | **0.9569** | 2,248 ms | 1× |
| v2 两阶段（+ Rerank） | 100% | 0.9538 | 9,547 ms | 2× |

**决策**：暂不上 Rerank（小知识库无收益，延迟 +325%）→ 这是真实大厂 PM 90% 的工作：**用数据拒绝不必要的优化**。

---

## 🛠 技术栈与决策

| 层 | 选型 | 为什么 |
|---|---|---|
| 后端框架 | **FastAPI** | Python AI 生态 + 自动 OpenAPI 文档 + 原生 async |
| 数据库 | MySQL 8.0 + Redis 7 | 业务数据 + 会话缓存 |
| 向量库 | **Qdrant** | CPU 友好（vs Milvus 需 GPU），Docker 一键起 |
| LLM | **DeepSeek-V3 Pro** | 中文优秀 + Function Calling 协议完整 |
| Embedding | **BAAI/bge-m3** | 中英双语 SOTA，硅基流动 API 免费 |
| Rerank | bge-reranker-v2-m3 | 已集成但暂未启用（评测数据决策）|
| 编排 | 自研 Agent Loop | 4 轮最大循环 + 意图检测 + 强制 tool_choice |
| 流式 | SSE (Server-Sent Events) | 比 WebSocket 简单 10 倍，单向流式够用 |
| 部署 | Docker Compose | 4 服务一键起：MySQL + Redis + Qdrant + Adminer |

### 多 Provider 路由架构（行业标准）

```
LLM 对话 / Function Call → DeepSeek 官方 API（功能完整）
Embedding 向量化         → 硅基流动 bge-m3（免费）
Rerank 精排              → 硅基流动 bge-reranker
```

**改 1 行 .env 配置切换供应商**，业务代码零改动 → 防供应商绑定。

---

## 🚦 项目进展

- [x] **W1 · 产品设计**：PRD v1.0 + 4 张用户卡 + Figma 原型 + GitHub 仓库
- [x] **W2 · 后端骨架**：Docker 四件套 + FastAPI 三层架构 + 4 张核心表 + POST /sessions
- [x] **W2 · LLM 接入**：硅基流动 → DeepSeek-V3，POST /messages 完整闭环 + 多轮上下文
- [x] **W3 · RAG 系统**：15 篇知识库 + 101 chunks + 带【1】【2】引用回答
- [x] **W3 · 评测体系**：65 题评测集 + 自动化脚本 + v1/v2 对比报告
- [x] **W4 · 流式输出**：SSE + status 事件 + 招呼语 bypass
- [x] **W4 · Agent 工具**：3 个工具（query_order / create_return_request / escalate_to_human）+ 意图检测 + 强制 tool_choice
- [x] **W4 · 情绪感知**：关键词词库 + 强度评分 + 共情 prompt 注入
- [ ] **W4 · React 前端** _（已有 HTML 测试页代替，正式 React 待 V2）_
- [ ] **W4 · Demo 视频** _（脚本已写，待录）_

---

## 📂 项目结构

```
CC-ai-customer-service/
├── backend/                        # FastAPI 后端
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py               # 配置（pydantic-settings）
│   │   ├── db/                     # MySQL / Redis / Qdrant 客户端
│   │   ├── models/                 # SQLAlchemy ORM (6 表)
│   │   ├── schemas/                # Pydantic 请求/响应
│   │   ├── services/               # 业务逻辑层
│   │   │   ├── llm_client.py       # LLM 封装（流式 + tools）
│   │   │   ├── embedding_client.py # Embedding API
│   │   │   ├── reranker_client.py  # Rerank API
│   │   │   ├── rag_service.py      # RAG 检索（两阶段）
│   │   │   ├── agent_tools.py      # 3 个 Agent 工具 + Mock 数据
│   │   │   ├── emotion_detector.py # 情绪检测
│   │   │   └── message_service.py  # 对话主流程（含 Agent loop）
│   │   └── routers/                # HTTP 接口
│   ├── scripts/                    # 工具脚本
│   │   ├── init_db.py              # 建表
│   │   ├── ingest.py               # 知识库灌库
│   │   ├── eval_rag.py             # RAG 评测
│   │   ├── test_llm.py             # LLM 连通测试
│   │   ├── test_tool_call.py       # Function calling 隔离测试
│   │   └── test_stream.html        # 流式 + Agent 演示页
│   ├── requirements.txt
│   └── .env.example
├── data/
│   ├── knowledge/                  # 15 篇知识库（退换货/物流/优惠/会员/商品/客服等）
│   └── eval/                       # 评测集（qa.jsonl + qa_hard.jsonl 共 65 题）
├── infra/
│   └── docker-compose.yml          # 4 服务：MySQL + Redis + Qdrant + Adminer
├── docs/
│   ├── PRD_v1.md                   # 产品需求文档
│   ├── db_schema.md                # 数据库设计文档
│   └── rag_evaluation_report.md    # RAG 评测对比报告
├── mockups/                        # UI 原型（SVG）
│   ├── 01_chat_page.svg            # 对话主页
│   └── 02_emotion_handling.svg     # 情绪安抚场景
└── README.md
```

---

## 🚀 快速开始

### 前置要求

- **Docker Desktop**（运行 MySQL/Redis/Qdrant）
- **Python 3.11**
- **Node.js 18+**（如需启动前端）
- 硅基流动 API Key（[注册送 14 元](https://siliconflow.cn)，Embedding 用）
- DeepSeek API Key（[注册送 ¥10](https://platform.deepseek.com)，LLM 用）

### 1. 克隆 + 启动数据库

```bash
git clone https://github.com/zchuchu0417/CC-ai-customer-service.git
cd CC-ai-customer-service

# 启动 4 服务（MySQL + Redis + Qdrant + Adminer）
cd infra && docker compose up -d
docker compose ps   # 应看到 4 个 Up
```

### 2. 后端环境

```bash
cd ../backend

# Python 虚拟环境
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
# source venv/bin/activate    # Mac/Linux

pip install -r requirements.txt

# 复制配置模板 + 填 API key
copy .env.example .env
# 编辑 .env，填 LLM_API_KEY 和 EMBEDDING_API_KEY
```

### 3. 初始化数据

```bash
# 建表（users / sessions / messages / feedback / knowledge_docs / doc_chunks）
python scripts/init_db.py

# 灌知识库（15 篇 → 101 chunks）
python scripts/ingest.py
```

### 4. 启动后端 + 测试

```bash
# 启动 FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

打开浏览器：
- **API 文档**：http://localhost:8000/docs
- **流式 + Agent 演示**：双击 `backend/scripts/test_stream.html`
- **数据库管理**：http://localhost:8080（用户 cc_user / 密码 cc_pass_2026）
- **Qdrant 控制台**：http://localhost:6333/dashboard

### 5. 跑评测

```bash
# v1 baseline（纯向量）
python scripts/eval_rag.py --file qa.jsonl,qa_hard.jsonl --output eval_v1.json

# v2 加 Rerank 对比
python scripts/eval_rag.py --file qa.jsonl,qa_hard.jsonl --rerank --output eval_v2.json
```

---

## 🎓 PM 视角的工程思考（项目最值钱的部分）

### 1. 拒绝不必要的优化
> 投入 1 天接入 Rerank，跑评测发现 **Recall 不变、MRR 微降、延迟 +325%、成本翻倍**。果断决策"暂不上线"+ 写入 PRD"未来触发条件"。**用数据拒绝优化，比堆功能更难**。

### 2. 解决 In-Context Learning Bias
> Agent 工具调用最初 0% 成功率：模型看到历史中的"稍等正在查询"模板（之前 AI 不调工具的失败 case），跟着继续装作调用又失败。
>
> **解法**：意图检测（正则匹配订单号/退货关键词）+ 强制 `tool_choice` 覆盖 → 工具调用成功率 0% → 95%+。
>
> 这是大厂 AI 产品上线后的核心治理工作之一。

### 3. 心理时间 vs 物理时间
> 在免费 API 受限的现状下，绝对延迟无法压到 1 秒。优化方向转为：
> - 推 SSE status 事件让用户从 0ms 看到"在干活"
> - 招呼语 bypass RAG 省 1 秒
> - 流式打字机心理感知比一次性输出快 10 倍
>
> **结论**：相同延迟下，体验差 10 倍 —— 心理时间才是 AI 产品真正战场。

### 4. 多 Provider 路由架构
> 不同能力（LLM / Embedding / Rerank）走不同最优供应商，改 .env 配置切换零代码改动。**防供应商绑定**是企业 AI 必备架构。

---

## 📚 文档矩阵

| 文档 | 用途 | 状态 |
|---|---|---|
| [PRD v1.0](./docs/PRD_v1.md) | 完整产品需求（用户画像/功能/指标/风险）| ✅ |
| [数据库 Schema](./docs/db_schema.md) | 6 张核心表 ER 设计 | ✅ |
| [RAG 评测报告](./docs/rag_evaluation_report.md) | v1 vs v2 对比 + 决策依据 | ✅ |
| [UI 原型](./mockups/README.md) | 对话主页 + 情绪安抚 SVG 原型 | ✅ |
| 部署文档 | 生产部署最佳实践 | ⏳ V2 |
| API 参考 | 接口契约（暂用 Swagger 自动文档代替）| 部分 |

---

## 🤝 致谢与参考

- [DeepSeek-V3](https://www.deepseek.com) · 国产 SOTA LLM
- [硅基流动 SiliconFlow](https://siliconflow.cn) · Embedding & Rerank 提供商
- [BGE 系列模型](https://huggingface.co/BAAI) · 智源研究院开源
- [Qdrant](https://qdrant.tech) · CPU 友好的开源向量数据库
- [FastAPI](https://fastapi.tiangolo.com) · Python 现代 Web 框架
- 知识库 mock 数据基于电商行业通用规则手工编写，不针对任何真实企业

---

## 👤 作者

**ZCC** · AI 产品经理（正在求职互联网大厂）

- 📧 邮箱：zchuchu827@gmail.com
- 🐱 GitHub：[@zchuchu0417](https://github.com/zchuchu0417)

> 这是一个从 0 到 1 的全栈实战项目：**产品设计 → 前后端开发 → RAG/Agent → 评测体系 → 项目复盘** 完整闭环，4 周冲刺完成。代码、文档、评测数据、踩坑日志全部开源。
>
> 欢迎面试官、AI PM 同行、想入门 RAG/Agent 的开发者一起交流 🙌

---

## 📜 License

[MIT](./LICENSE) © 2026 ZCC
