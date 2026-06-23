"""测试 LLM API 连通性

用法：
    python scripts/test_llm.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from app.config import settings


def main():
    print(f"🔌 连接 LLM:")
    print(f"   provider = {settings.llm_provider}")
    print(f"   base_url = {settings.llm_base_url}")
    print(f"   model    = {settings.llm_model}")
    print(f"   key      = {settings.llm_api_key[:8]}...{settings.llm_api_key[-4:] if len(settings.llm_api_key) > 12 else ''}")
    print()

    if not settings.llm_api_key:
        print("❌ LLM_API_KEY 没配，请检查 backend/.env")
        return

    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    print("📤 发送：你好，请用一句话介绍你自己")
    start = time.time()

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": "你是 CC 商城的智能客服助手。"},
            {"role": "user", "content": "你好，请用一句话介绍你自己"},
        ],
        max_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
    )

    latency = int((time.time() - start) * 1000)
    answer = response.choices[0].message.content
    usage = response.usage

    print(f"\n📥 收到（{latency}ms，{usage.total_tokens} tokens）:")
    print(f"   {answer}")
    print()
    print("✅ LLM 通了！可以进 Day 5 下午块。")


if __name__ == "__main__":
    main()