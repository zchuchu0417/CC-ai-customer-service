"""最纯粹的 function calling 隔离测试

不带 RAG、不带历史，就 1 个工具 + 1 个问题，看 API 到底支不支持。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from app.config import settings


print("=" * 60)
print("Function Calling 隔离测试")
print("=" * 60)
print(f"Provider: {settings.llm_provider}")
print(f"Base URL: {settings.llm_base_url}")
print(f"Model:    {settings.llm_model}")
print(f"Key:      {settings.llm_api_key[:8]}...{settings.llm_api_key[-4:]}")
print()

client = OpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
)

# 最简单的工具定义
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的实时天气，需要城市名作为参数",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "中文城市名，如：北京、上海",
                    },
                },
                "required": ["city"],
            },
        },
    }
]

# 最简单的问题（应该明确触发工具调用）
messages = [
    {
        "role": "system",
        "content": "你是一个助手。如果需要查询天气，必须调用 get_weather 工具，不要凭空编造。",
    },
    {
        "role": "user",
        "content": "上海今天天气怎么样？",
    },
]

print("📤 发送测试请求...")
print(f"   tools 参数: {len(tools)} 个工具")
print(f"   tool_choice: auto")
print()

try:
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    msg = response.choices[0].message
    finish_reason = response.choices[0].finish_reason

    print("📥 API 响应:")
    print(f"   finish_reason: {finish_reason}")
    print(f"   content:       {msg.content!r}")
    print(f"   tool_calls:    {msg.tool_calls}")
    print(f"   usage:         {response.usage}")
    print()

    if msg.tool_calls:
        print("✅ Function calling 工作！")
        for tc in msg.tool_calls:
            print(f"   工具名: {tc.function.name}")
            print(f"   参数:   {tc.function.arguments}")
    else:
        print("❌ Function calling 失败：API 返回了 content 但没有 tool_calls")
        print("   → 说明当前 model + provider 不支持 function calling")
        print("   → 需要换模型或换 provider")

except Exception as e:
    print(f"❌ API 调用异常: {e}")
