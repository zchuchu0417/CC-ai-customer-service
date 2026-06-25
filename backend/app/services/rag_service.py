"""RAG 检索服务（v2 · 支持 Rerank）

两阶段检索：
    1. 召回：Qdrant 向量检索，取 top_recall（默认 20）
    2. 精排：Reranker 模型对 20 个候选重新打分，取 top_k（默认 5）

通过 use_rerank=False 可降级回纯向量检索（用于对比评测）
"""
from app.db.qdrant import qdrant_client
from app.services.embedding_client import embedding_client
from app.services.reranker_client import reranker_client


COLLECTION_NAME = "cc_knowledge"
DEFAULT_TOP_K = 5
DEFAULT_TOP_RECALL = 20  # rerank 前的粗召数量
MIN_SCORE = 0.3


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = MIN_SCORE,
    use_rerank: bool = True,
) -> list[dict]:
    """检索与 query 最相关的 top_k 个 chunks

    Args:
        query: 用户提问
        top_k: 返回数量
        min_score: 最低相关性阈值（rerank 模式下指 rerank score，纯向量模式下指 vector score）
        use_rerank: True=两阶段（向量召回 + Rerank 精排），False=纯向量

    Returns:
        [
            {
                "score": 0.95,             # 最终分数（rerank 或 vector）
                "vector_score": 0.78,      # 原始向量分数（仅 rerank 模式下有）
                "title": "...",
                "category": "退换货",
                "section": "...",
                "content": "...",
                "doc_id": 1,
                "chunk_index": 0,
                "vector_id": "uuid",
            },
            ...
        ]
    """
    # === Step 1: 向量召回 ===
    query_vec = embedding_client.embed(query)

    # rerank 模式：召回 top_recall 候选；纯向量模式：直接召回 top_k
    recall_limit = DEFAULT_TOP_RECALL if use_rerank else top_k
    candidates = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vec,
        limit=recall_limit,
        score_threshold=0.0,  # 阈值过滤交给最后一步统一做
    )

    if not candidates:
        return []

    # === Step 2: Rerank 精排（可选）===
    if use_rerank:
        # 注意：留出 Top-15 给 reranker（>top_k 但不必全部 20，省钱）
        documents = [c.payload.get("content", "") for c in candidates]
        try:
            reranked = reranker_client.rerank(query, documents, top_n=top_k)
        except Exception as e:
            # rerank 失败降级为纯向量
            print(f"⚠️ Rerank 失败，降级纯向量: {e}")
            return _build_results(candidates[:top_k], min_score, use_vector_score=True)

        # 按 rerank 结果重组
        results = []
        for r in reranked:
            if r["score"] < min_score:
                continue
            orig = candidates[r["index"]]
            results.append({
                "score": r["score"],
                "vector_score": round(orig.score, 4),
                "title": orig.payload.get("title"),
                "category": orig.payload.get("category"),
                "section": orig.payload.get("section"),
                "content": orig.payload.get("content"),
                "doc_id": orig.payload.get("doc_id"),
                "chunk_index": orig.payload.get("chunk_index"),
                "vector_id": str(orig.id),
            })
        return results

    # 纯向量模式
    return _build_results(candidates[:top_k], min_score, use_vector_score=True)


def _build_results(candidates: list, min_score: float, use_vector_score: bool) -> list[dict]:
    """整理纯向量检索结果"""
    return [
        {
            "score": round(c.score, 4),
            "title": c.payload.get("title"),
            "category": c.payload.get("category"),
            "section": c.payload.get("section"),
            "content": c.payload.get("content"),
            "doc_id": c.payload.get("doc_id"),
            "chunk_index": c.payload.get("chunk_index"),
            "vector_id": str(c.id),
        }
        for c in candidates
        if c.score >= min_score
    ]


def format_context(chunks: list[dict]) -> str:
    """把检索到的 chunks 格式化成 Prompt 里的'参考资料'区"""
    if not chunks:
        return "（未找到相关参考资料）"

    parts = []
    for i, c in enumerate(chunks, 1):
        section = f"，{c['section']}" if c.get("section") else ""
        parts.append(
            f"【{i}】（来源：{c['title']}{section}）\n{c['content']}"
        )
    return "\n\n---\n\n".join(parts)


def build_citations(chunks: list[dict]) -> list[dict]:
    """生成简化的引用列表（存进 message.citations 字段，给前端展示）"""
    return [
        {
            "index": i,
            "title": c["title"],
            "section": c["section"],
            "content_preview": c["content"][:120] + ("…" if len(c["content"]) > 120 else ""),
            "score": c["score"],
            "vector_score": c.get("vector_score"),
            "doc_id": c["doc_id"],
            "category": c["category"],
        }
        for i, c in enumerate(chunks, 1)
    ]
