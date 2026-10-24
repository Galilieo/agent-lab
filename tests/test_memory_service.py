"""验证记忆提取调用的请求组织、正文解析与无效结果拒绝。

fake HTTP client 隔离真实模型；LLM 请求组装、响应解析与 Pydantic 校验
由本地源码真实执行。不写数据库，也不证明真实模型的记忆判断质量。
"""

import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from app.services import memory


@pytest.fixture
def extraction_http(monkeypatch):
    """替换外部 HTTP 调用，允许各场景指定模型正文并观察发出的消息。"""
    observed = {}

    def configure(answer):
        class FakeAsyncClient:
            def __init__(self, *, timeout=None):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def post(self, url, *, headers, json):
                # 只观察任务消息，不保留请求头或密钥。
                observed["messages"] = json["messages"]
                return httpx.Response(
                    200,
                    request=httpx.Request("POST", url),
                    json={
                        "id": "test-memory-extraction",
                        "object": "chat.completion",
                        "created": 0,
                        "model": "test-model",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": "stop",
                                "message": {
                                    "role": "assistant",
                                    "content": answer,
                                    "tool_calls": [],
                                },
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 5,
                            "total_tokens": 15,
                        },
                    },
                )

        monkeypatch.setattr("app.services.llm.httpx.AsyncClient", FakeAsyncClient)
        monkeypatch.setattr(
            "app.services.llm.settings.openai_base_url", "https://llm.invalid/v1"
        )
        monkeypatch.setattr("app.services.llm.settings.openai_api_key", "test-key")
        monkeypatch.setattr("app.services.llm.settings.openai_model", "test-model")
        return observed

    return configure


def test_extract_memories_uses_extraction_prompt_and_validates_content(extraction_http):
    """验证专用系统指令、本轮用户消息，以及正文到候选模型的解析。"""
    message = "记住，以后默认用中文回答。"
    observed = extraction_http(
        json.dumps(
            {
                "action": "upsert",
                "memories": [
                    {"scope": "user", "key": "answer_language", "value": " 中文 "}
                ],
            },
            ensure_ascii=False,
        )
    )

    result = asyncio.run(memory.extract_memories(message))

    # 完整结果比较保护字段保留与去空白处理，不能直接返回未校验的原始正文。
    assert result.model_dump() == {
        "action": "upsert",
        "memories": [
            {
                "scope": "user",
                "key": "answer_language",
                "value": "中文",
            }
        ],
    }

    # 检查真实请求组装结果，避免仍使用普通聊天指令或遗漏本轮用户消息。
    assert observed["messages"][0]["role"] == "system"
    assert observed["messages"][0]["content"] != "You are a helpful assistant."
    assert observed["messages"][1] == {
        "role": "user",
        "content": message,
    }


def test_extract_memories_rejects_non_json_content(extraction_http):
    """HTTP 与外层 JSON 成功，但正文不是合法提取 JSON 时应报告校验失败。"""
    extraction_http("好的，我记住了")

    # 非 JSON 正文必须报告失败；静默转为 skip 会使此断言失败。
    with pytest.raises(ValidationError):
        asyncio.run(
            memory.extract_memories("记住，以后默认用中文回答。")
        )
