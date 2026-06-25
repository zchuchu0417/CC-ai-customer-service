# RAG 检索优化实验报告 v1.0

> 日期：2026-06-24
> 项目：CC 商城 AI 客服助手
> 实验者：ZCC（AI 产品经理）

## 1. 实验背景

W3 阶段完成了基础 RAG 检索（向量召回 + LLM 生成）。本实验目的是评估**是否应该接入 Reranker 精排模型**，决策是否将其上线。

行业最佳实践通常是「**两阶段检索**」：
1. **召回阶段**：Embedding 向量检索，取 Top-N 粗候选
2. **精排阶段**：Reranker（cross-encoder）对 N 个候选打分，取 Top-K 精排结果

但「最佳实践 ≠ 一定适合本项目」。需要数据验证。

## 2. 实验设计

### 2.1 评测集
- **`qa.jsonl`**: 50 题，覆盖 11 类业务场景，标准用户提问表达
- **`qa_hard.jsonl`**: 15 题，模拟真实用户口语化、错别字、模糊表达
- **合并集**: 65 题

每条 QA 含：
- `question`: 用户提问
- `expected_doc_ids`: 期望命中的知识库文档 ID（人工标注）
- `category`: 业务分类

### 2.2 对比方案

| 方案 | Embedding | 召回 | 精排 |
|---|---|---|---|
| **v1 baseline** | BAAI/bge-m3 | Qdrant top-5 | 无 |
| **v2 rerank** | BAAI/bge-m3 | Qdrant top-20 | BAAI/bge-reranker-v2-m3, 选 top-5 |

### 2.3 指标
- **Recall@5**: top-5 至少包含一个 expected doc 的比例
- **MRR**: 平均倒数排名（首个命中 doc 在 top-5 的位置）
- **平均延迟**: 端到端检索耗时

## 3. 实验结果

### 3.1 整体指标对比

| 指标 | v1 纯向量 | v2 Rerank | 变化 |
|---|---:|---:|---:|
| Recall@5 | 100.0% | 100.0% | 持平 |
| MRR | 0.9569 | 0.9538 | **-0.3%** |
| 平均延迟 | 2,248 ms | 9,547 ms | **+325%** |
| API 调用 | 1 次 / query | 2 次 / query | +100% 成本 |

### 3.2 关键观察

1. **召回已达天花板**：v1 baseline 已 100% 召回，没有改进空间
2. **MRR 微降而非提升**：Rerank 偶尔将"严格匹配文档"排到第二位，引入"次优但仍相关"的文档为 top-1
3. **延迟代价高**：增加约 7 秒/query，对用户体验有显著影响
4. **成本翻倍**：每次问答多 1 次 API 调用

### 3.3 MRR 微降的根因分析

实例：QA #1 "鞋子可以7天无理由退货吗"，标注 expected_doc_ids = [1, 9]
- **v1**: top-1 命中 doc_id=9（跑鞋手册退货段），MRR = 1.0
- **v2**: top-1 改为 doc_id=2（质量问题处理，含"商品有问题"语义），doc_id=9 退到 top-2，MRR = 0.5

**这不是 Rerank 错误**，而是：
- doc_id=2 在语义上确实也合理
- 评测集人工标注未穷举所有合理答案
- 真实业务里这种"模糊正确"是常态

## 4. 决策与结论

### 4.1 当前决策
**暂不在生产环境启用 Rerank**。理由：

1. **现状无优化空间**：召回率 100%、MRR 0.96，已接近天花板
2. **代价显著**：延迟 +325%、成本 +100%
3. **业务规模未达阈值**：当前 100 chunks，远小于 Rerank 真正发挥价值的规模（>10K chunks）

### 4.2 保留 Rerank 代码
- `app/services/reranker_client.py` 保留
- `rag_service.retrieve()` 保留 `use_rerank=False` 默认参数
- 通过 **1 行配置切换**，未来可随时开启

### 4.3 触发重启 Rerank 的条件
- 知识库扩大到 ≥ 5000 chunks
- 上线后 Bad Case 池显示「召回到了但排序错位」≥ 10% 占比
- 用户反馈中"答非所问但相关"投诉持续上升

## 5. PM 视角的元结论

> **优化的最高境界不是「上了多少新技术」，而是「拒绝了多少不必要的优化」。**
>
> 本次实验最大价值是「用 65 条评测数据证明了 Rerank 在当前阶段不该上」，避免了：
> - 用户体验下降（响应慢 3 倍）
> - 成本翻倍
> - 系统复杂度上升
>
> 这是 AI 产品经理日常 90% 的工作 —— **做正确的取舍**，比堆功能更难。

## 6. 后续待办

| 优先级 | 任务 | 预期收益 |
|---|---|---|
| 高 | 流式输出（SSE）改造对话接口 | 首 Token 响应 < 1s，用户体感质变 |
| 高 | Agent 工具调用（订单查询、退货创建、转人工） | 从"问答"到"执行" |
| 中 | 扩展评测集（增加跨文档、负样本、对抗样本）| 评测更逼近真实分布 |
| 中 | 知识库治理工具（管理后台 CRUD）| 运营效率 |
| 低 | 知识库扩到 1000+ chunks 后重启 Rerank 评估 | 触发条件后再做 |

## 附录 · 复现实验命令

```bash
cd backend && .\venv\Scripts\Activate.ps1

# v1 baseline
python scripts/eval_rag.py --file qa.jsonl,qa_hard.jsonl --output eval_v1.json

# v2 rerank
python scripts/eval_rag.py --file qa.jsonl,qa_hard.jsonl --rerank --output eval_v2.json
```

---

> 数据来源：`backend/eval_v1.json`、`backend/eval_v2.json`（实验产物，已 .gitignore）  
> 评测脚本：`backend/scripts/eval_rag.py`  
> 评测集：`data/eval/qa.jsonl`、`data/eval/qa_hard.jsonl`
