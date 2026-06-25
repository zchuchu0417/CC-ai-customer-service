"""RAG 自动化评测脚本

用法（在 backend/ 目录，激活 venv 后）：
    python scripts/eval_rag.py                  # 评测默认配置
    python scripts/eval_rag.py --top-k 5        # 改 top-k
    python scripts/eval_rag.py --output v1.json # 把结果存文件

输出指标：
- Recall@5：top-5 至少包含一个 expected doc 的比例
- Recall@K：（K 可配置）
- MRR：平均倒数排名（命中越靠前分数越高）
- 平均延迟、分类细分指标
"""
import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import rag_service


# ============ 配置 ============
EVAL_DIR = Path(__file__).parent.parent.parent / "data" / "eval"
DEFAULT_EVAL_FILE = EVAL_DIR / "qa.jsonl"


def load_eval_set(path: Path) -> list[dict]:
    """读取 JSONL 评测集"""
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def evaluate_one(item: dict, top_k: int, use_rerank: bool) -> dict:
    """评测单条"""
    start = time.time()
    try:
        chunks = rag_service.retrieve(
            item["question"],
            top_k=top_k,
            min_score=0.0,
            use_rerank=use_rerank,
        )
    except Exception as e:
        return {
            "id": item["id"],
            "error": str(e)[:100],
            "hit": False,
            "rank": 0,
            "latency_ms": 0,
        }
    latency_ms = int((time.time() - start) * 1000)

    expected = set(item["expected_doc_ids"])
    retrieved_doc_ids = [c["doc_id"] for c in chunks]

    # 找命中的最高排名（1 起算）
    rank = 0
    for i, doc_id in enumerate(retrieved_doc_ids, 1):
        if doc_id in expected:
            rank = i
            break

    return {
        "id": item["id"],
        "question": item["question"],
        "category": item.get("category", "unknown"),
        "expected_doc_ids": list(expected),
        "retrieved_doc_ids": retrieved_doc_ids,
        "retrieved_titles": [c["title"] for c in chunks],
        "top_scores": [c["score"] for c in chunks],
        "hit": rank > 0,
        "rank": rank,
        "reciprocal_rank": 1.0 / rank if rank > 0 else 0.0,
        "latency_ms": latency_ms,
    }


def aggregate(results: list[dict], top_k: int) -> dict:
    """汇总指标"""
    total = len(results)
    hits = sum(1 for r in results if r.get("hit"))
    mrr = sum(r.get("reciprocal_rank", 0) for r in results) / total if total else 0
    avg_latency = sum(r["latency_ms"] for r in results) / total if total else 0

    # 分类细分
    by_cat = defaultdict(lambda: {"total": 0, "hits": 0})
    for r in results:
        cat = r.get("category", "unknown")
        by_cat[cat]["total"] += 1
        if r.get("hit"):
            by_cat[cat]["hits"] += 1

    return {
        "total_questions": total,
        f"recall@{top_k}": round(hits / total, 4) if total else 0,
        "mrr": round(mrr, 4),
        "hits": hits,
        "misses": total - hits,
        "avg_latency_ms": round(avg_latency, 1),
        "by_category": {
            cat: {
                "total": v["total"],
                "hits": v["hits"],
                "recall": round(v["hits"] / v["total"], 4) if v["total"] else 0,
            }
            for cat, v in by_cat.items()
        },
    }


def print_summary(summary: dict, results: list[dict], top_k: int):
    """美观打印"""
    print("\n" + "=" * 60)
    print("📊 RAG 评测结果")
    print("=" * 60)
    print(f"总问题数：{summary['total_questions']}")
    print(f"Recall@{top_k}：{summary[f'recall@{top_k}']:.2%}  （{summary['hits']} 命中 / {summary['misses']} 漏召）")
    print(f"MRR：{summary['mrr']:.4f}  （越高越好，1.0 = 全部排第一）")
    print(f"平均延迟：{summary['avg_latency_ms']:.1f} ms")
    print()

    print("📂 分类指标：")
    for cat, stat in sorted(summary["by_category"].items()):
        print(f"   {cat:8s}  {stat['hits']:2d}/{stat['total']:2d}  recall={stat['recall']:.2%}")

    print()
    print("❌ 漏召案例（前 10 条）：")
    misses = [r for r in results if not r.get("hit")][:10]
    if not misses:
        print("   （无）🎉")
    for m in misses:
        print(f"   #{m['id']:2d} [{m['category']}] {m['question']}")
        print(f"        期望 doc_ids: {m['expected_doc_ids']}")
        print(f"        实际 top-{top_k}: {m['retrieved_doc_ids']}")
        if m.get("retrieved_titles"):
            print(f"        实际 top-1: {m['retrieved_titles'][0]} (score={m['top_scores'][0]:.4f})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=5, help="检索 top-k")
    parser.add_argument("--file", type=str, default="qa.jsonl",
                        help="评测集文件名（data/eval/ 下）。多个用逗号分隔合并跑")
    parser.add_argument("--rerank", action="store_true",
                        help="启用 Rerank 精排（v2）。不加则是纯向量（v1 baseline）")
    parser.add_argument("--output", type=str, default=None, help="结果输出到 JSON 文件")
    args = parser.parse_args()

    # 支持多文件合并
    files = [EVAL_DIR / name.strip() for name in args.file.split(",")]
    items = []
    for f in files:
        print(f"📂 加载评测集：{f.name}")
        items.extend(load_eval_set(f))
    print(f"📚 共 {len(items)} 条评测问题")
    print(f"🎯 top_k = {args.top_k}")
    print(f"🔧 模式 = {'v2 Rerank（两阶段）' if args.rerank else 'v1 纯向量（baseline）'}")
    print()

    results = []
    for i, item in enumerate(items, 1):
        result = evaluate_one(item, args.top_k, args.rerank)
        results.append(result)
        marker = "✓" if result["hit"] else "✗"
        print(f"  [{i:2d}/{len(items)}] {marker} #{item['id']:2d} {item['question']}")

    summary = aggregate(results, args.top_k)
    print_summary(summary, results, args.top_k)

    if args.output:
        Path(args.output).write_text(
            json.dumps({"summary": summary, "details": results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n💾 详细结果已写入 {args.output}")


if __name__ == "__main__":
    main()
