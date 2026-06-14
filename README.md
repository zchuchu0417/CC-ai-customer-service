# 🛒 CC 商城 AI 客服助手

> 企业级 AI 智能问答系统 · RAG + Agent · 全栈落地
>
> **Enterprise AI Customer Service Q&A System** — built end-to-end by an AI PM.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/status-WIP-orange)]()
[![Stage](https://img.shields.io/badge/stage-W1%20Design-blue)]()

---

## 📌 一句话项目定义

面向电商 C 端用户的智能问答系统，回答**退换货 / 物流 / 优惠 / 商品参数**4 类问题，通过 **RAG** 给出带原文出处的回答，并具备**情绪感知能力**——检测到负面情绪时优先共情和转人工；必要时通过 **Agent** 调用订单查询、退换货单创建、人工转接 3 个工具完成执行。

## 🎯 解决什么问题

据艾瑞咨询 2024 年报告，电商客服日均咨询量中 **65% 为重复性问题**，但人工客服平均响应时间 **3-5 分钟**，旺季高峰可达 30 分钟以上。本项目目标：

- 单次问答自助解决率 **≥ 70%**（北极星指标）
- 答案采纳率 **≥ 75%**
- 首 Token 响应 **≤ 1 秒**
- 降低 **30%** 人工客服压力

## 🏗 系统架构

```
用户提问 → Query 改写 → 混合检索（向量+BM25）→ Rerank → LLM 生成 → 流式返回
                              ↓
                  情绪感知 + Agent 工具调用
```

## 📚 文档导航

| 文档 | 内容 |
|---|---|
| [📄 PRD v1.0](./docs/PRD_v1.md) | 完整产品需求文档（用户画像、功能、指标、风险） |
| [🎨 UI 原型](./mockups/README.md) | 对话主页 / 情绪安抚场景原型图 |
| [🛠 开发文档](./docs/) | 接口契约、数据库设计、部署指南（开发中） |

## 🚀 技术栈

| 层 | 选型 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + Ant Design |
| 后端 | FastAPI (Python 3.11) + SQLAlchemy |
| 数据库 | MySQL 8.0 + Redis 7 |
| 向量库 | Qdrant（CPU 友好，本地部署） |
| LLM | DeepSeek-Chat (API) |
| Embedding | bge-m3（硅基流动 API） |
| Rerank | bge-reranker-base（本地 CPU） |
| 编排 | LangChain + 自研 Agent |

## 📅 4 周冲刺路线

- [x] **W1** · PRD + Figma 原型 + 开发环境
- [ ] **W2** · 后端骨架 + 数据库 + 知识库灌库
- [ ] **W3** · RAG 闭环 + 前端对话页
- [ ] **W4** · Agent + 评测 + Demo 上线

## 👤 项目作者

**ZCC** · AI 产品经理（应聘中）

> 这是一个从 0 到 1 的全栈实战项目，覆盖产品设计 → 前后端开发 → RAG/Agent → 评测 → 上线的完整链路。每周持续更新中。

## 📜 License

MIT