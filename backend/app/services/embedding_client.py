"""Embedding 客户端 - 把文本转向量

硅基流动支持 OpenAI 兼容的 /v1/embeddings 端点，直接复用 OpenAI SDK。
默认模型：BAAI/bge-m3（1024 维，中英文俱佳，硅基流动免费额度内）

PM 视角：
- Embedding 模型决定"语义检索"的上限
- 同一个 bge-m3 模型在所有 OpenAI 兼容厂商表现一致
- 后续可改成 Qwen3-Embedding、智谱 embedding-2 等
"""
from openai import OpenAI
from app.config import settings


# 硅基流动免费 embedding 模型
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIMENSIONS = 1024  # bge-m3 输出维度


class EmbeddingClient:
    def __init__(self):
        if not settings.llm_api_key:
            raise ValueError("LLM_API_KEY 未配置")

        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=30.0,
        )
        self.model = DEFAULT_EMBEDDING_MODEL

    def embed(self, text: str) -> list[float]:
        """单个文本转向量"""
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量文本转向量（更省 API 调用次数）"""
        # 硅基流动单次最多 32 条，超出分批
        BATCH_SIZE = 32
        all_embeddings = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
            )
            all_embeddings.extend([d.embedding for d in response.data])
        return all_embeddings


# 全局单例
embedding_client = EmbeddingClient()
