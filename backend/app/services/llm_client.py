"""LLM 客户端封装

为什么单独封装一层？
1. 业务代码不依赖 OpenAI SDK，未来换 SDK 不动业务
2. 集中处理 token 统计、超时、错误转换
3. 后续可加 retry、cache、rate-limit 等横切关注点
"""
import time
from openai import OpenAI
from app.config import settings


class LLMClient:
    """OpenAI 兼容协议的统一封装（硅基流动 / DeepSeek 直连 / 智谱 等都用这一套）"""

    def __init__(self):
        if not settings.llm_api_key:
            raise ValueError("LLM_API_KEY 未配置，请检查 backend/.env")

        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=30.0,
        )
        self.model = settings.llm_model
        self.max_tokens = settings.llm_max_tokens
        self.temperature = settings.llm_temperature

    def chat(
        self,
        messages: list[dict],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict:
        """调用 LLM，返回结构化结果

        Args:
            messages: [{"role": "system|user|assistant", "content": "..."}]
            max_tokens: 覆盖默认
            temperature: 覆盖默认

        Returns:
            {
                "content": str,         # AI 回复文本
                "tokens": int,          # 总 token 数（含输入和输出）
                "latency_ms": int,      # 调用耗时
                "model": str,           # 实际响应中的模型名
            }
        """
        start = time.time()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens or self.max_tokens,
            temperature=(
                temperature if temperature is not None else self.temperature
            ),
        )

        latency_ms = int((time.time() - start) * 1000)

        return {
            "content": response.choices[0].message.content,
            "tokens": response.usage.total_tokens if response.usage else 0,
            "latency_ms": latency_ms,
            "model": response.model or self.model,
        }


# 全局单例（首次 import 时初始化）
llm_client = LLMClient()
