"""LLM 客户端封装（支持非流式 + 流式两种模式）"""
import time
from collections.abc import Iterator
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

    def chat_stream(
        self,
        messages: list[dict],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Iterator[dict]:
        """流式调用 LLM，逐 token yield

        Yields:
            事件序列:
                {"type": "token", "content": "你"}      ← 每次一个/几个 token
                {"type": "token", "content": "好"}
                ...
                {"type": "done",                        ← 流结束
                 "full_content": "你好，关于...",
                 "tokens": 357,
                 "latency_ms": 7158,
                 "model": "deepseek-ai/DeepSeek-V3"}
        """
        start = time.time()
        full_content_parts = []
        total_tokens = 0
        actual_model = self.model

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens or self.max_tokens,
            temperature=(
                temperature if temperature is not None else self.temperature
            ),
            stream=True,
            stream_options={"include_usage": True},  # 让最后一帧带 usage 统计
        )

        for chunk in stream:
            # 流式过程中：每帧含 1+ 个 token
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_content_parts.append(delta.content)
                    yield {"type": "token", "content": delta.content}

            # 流结束帧：usage 在这里
            if chunk.usage:
                total_tokens = chunk.usage.total_tokens
            if chunk.model:
                actual_model = chunk.model

        latency_ms = int((time.time() - start) * 1000)
        yield {
            "type": "done",
            "full_content": "".join(full_content_parts),
            "tokens": total_tokens,
            "latency_ms": latency_ms,
            "model": actual_model,
        }


# 全局单例（首次 import 时初始化）
llm_client = LLMClient()
