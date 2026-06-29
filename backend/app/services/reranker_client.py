"""Reranker 客户端 - 精排模型

Rerank 模型做的事：
    输入: query + N 个候选 documents
    输出: 每个 document 的"真实相关性分数"（0-1）
    用途: 在 Top-N 粗召后做精排，把最相关的提到前面

vs Embedding 检索:
    - Embedding 是"对称"匹配（query 和 doc 都向量化后算余弦）
    - Rerank 是"交叉"匹配（query 和 doc 一起送进 cross-encoder，更精准但更慢）
    - 行业最佳实践：粗召 top-20 → rerank → top-5

API 选型：硅基流动 BAAI/bge-reranker-v2-m3（免费，中英文俱佳）
"""
import httpx
from app.config import settings


RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


class RerankerClient:
    def __init__(self):
        # Reranker 也走硅基流动（DeepSeek 没此端点）
        api_key = settings.embedding_api_key or settings.llm_api_key
        if not api_key:
            raise ValueError("EMBEDDING_API_KEY 或 LLM_API_KEY 至少配一个")
        self.api_key = api_key
        self.endpoint = settings.embedding_base_url.rstrip("/") + "/rerank"
        self.model = RERANKER_MODEL

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int | None = None,
    ) -> list[dict]:
        """对一组 documents 精排

        Args:
            query: 用户问题
            documents: 候选文档内容列表
            top_n: 返回前 N 个，默认全部

        Returns:
            [{"index": 原下标, "score": 相关性分数 0-1}, ...]
            按 score 从高到低排序
        """
        if not documents:
            return []

        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "return_documents": False,
        }
        if top_n:
            payload["top_n"] = min(top_n, len(documents))

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        # 标准返回：{"results": [{"index": 0, "relevance_score": 0.95}, ...]}
        return [
            {"index": r["index"], "score": round(r["relevance_score"], 4)}
            for r in data.get("results", [])
        ]


# 全局单例
reranker_client = RerankerClient()
