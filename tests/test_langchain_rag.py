"""验证框架严格RAG链，真实运行检索/预算/模板/SDK/引用检查。

使用临时Chroma和人工向量，问题Embedding与聊天HTTP被替代。
预设回答不证明模型理解或语义忠实，只检查本项目的编排与来源契约。
"""

import asyncio
import json

import httpx
import pytest
from langchain_core.messages import AIMessage
from langchain_deepseek import ChatDeepSeek

from app.services import langchain_rag, rag_retrieval
from app.services.langchain_callbacks import ModelCallRecorder
from app.services.rag import DocumentChunk
from app.services.vector_store import open_notes_collection, upsert_chunks


@pytest.fixture
def offline_rag(monkeypatch):
    """保留真实框架及本地检索，为回答请求提供一份预设HTTP响应。"""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setattr(langchain_rag.settings, "openai_api_key", "offline-placeholder")
    monkeypatch.setattr(
        langchain_rag.settings, "openai_base_url", "https://example.invalid/v1"
    )
    monkeypatch.setattr(langchain_rag.settings, "openai_model", "offline-model")

    async def fake_embedding(texts):
        return [[1.0] + [0.0] * 1023 for _ in texts]

    monkeypatch.setattr(rag_retrieval, "embed_texts", fake_embedding)
    observed = []

    async def run(index_dir, answer, *, history=None, max_chars=4000, callbacks=None):
        def respond(request):
            observed.append(json.loads(request.content))
            return httpx.Response(200, json={
                "id": "offline-rag",
                "object": "chat.completion",
                "created": 0,
                "model": "offline-model",
                "choices": [{
                    "index": 0, "finish_reason": "stop",
                    "message": {"role": "assistant", "content": answer},
                }],
                "usage": {
                    "prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12,
                },
            })

        with httpx.Client(transport=httpx.MockTransport(respond)) as sync_http:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(respond)
            ) as async_http:
                def create_model(**kwargs):
                    return ChatDeepSeek(
                        **kwargs,
                        http_client=sync_http,
                        http_async_client=async_http,
                    )

                monkeypatch.setattr(langchain_rag, "ChatDeepSeek", create_model)
                return await langchain_rag.answer_with_langchain_rag(
                    "何时释放连接？", index_dir, history,
                    top_k=2, max_chars=max_chars, callbacks=callbacks,
                )

    return run, observed


@pytest.fixture
def seeded_index(tmp_path):
    """人工向量让短片段排第一，第二片段故意超过后续250字符预算。"""
    index_dir = tmp_path / "chroma"
    chunks = [
        DocumentChunk("notes/a.md", 0, 0, 6, "连接先关闭。"),
        DocumentChunk("notes/b.md", 0, 0, 500, "长" * 500),
    ]
    collection = open_notes_collection(index_dir)
    upsert_chunks(collection, chunks, [
        [1.0] + [0.0] * 1023,
        [0.0, 1.0] + [0.0] * 1022,
    ])
    return index_dir


def test_rag_chain_checks_only_delivered_sources_and_preserves_raw_response(
    seeded_index, offline_rag
):
    """实际只交付短片段，未交付引用需标注；展示处理不修改原始模型响应。"""
    run, observed = offline_rag
    history = [{"role": "assistant", "content": "继续。"}]
    recorder = ModelCallRecorder()
    raw_answer = "先关闭[notes/a.md::0]，再确认[notes/a.md::0]。[notes/b.md::0]"

    result = asyncio.run(run(
        seeded_index, raw_answer, history=history, max_chars=250,
        callbacks=[recorder],
    ))

    assert len(observed) == 1
    sent = observed[0]["messages"]
    assert [message["role"] for message in sent] == ["system", "user", "assistant", "user"]
    assert "资料不足" in sent[0]["content"]
    assert json.loads(sent[1]["content"].removeprefix("RAG Context:\n")) == [{
        "id": "notes/a.md::0", "source": "notes/a.md", "chunk_index": 0,
        "start": 0, "end": 6, "text": "连接先关闭。",
    }]
    assert sent[2] == {"role": "assistant", "content": "继续。"}
    assert sent[3] == {"role": "user", "content": "何时释放连接？"}
    assert result.answer == (
        "先关闭[notes/a.md::0]，再确认[notes/a.md::0]。[引用未找到]"
        "\n\n提示：部分引用无法对应到本轮资料，请核对原文。"
    )
    assert result.sources == [DocumentChunk("notes/a.md", 0, 0, 6, "连接先关闭。")]
    assert result.invalid_ids == ["notes/b.md::0"]
    assert isinstance(result.response, AIMessage)
    assert result.response.content == raw_answer
    assert result.response.usage_metadata["total_tokens"] == 12
    assert len(recorder.records) == 1
    assert recorder.records[0].outcome == "succeeded"
    assert history == [{"role": "assistant", "content": "继续。"}]


@pytest.mark.parametrize("empty_index", [True, False], ids=["empty-index", "zero-budget"])
def test_rag_chain_skips_model_when_no_material_is_deliverable(
    empty_index, seeded_index, tmp_path, offline_rag
):
    """空检索及预算筛选为空均由应用短路，不能请求回答模型或伪造响应。"""
    run, observed = offline_rag
    index_dir = tmp_path / "empty" if empty_index else seeded_index
    result = asyncio.run(run(
        index_dir, "这份模拟回答不应被使用。", max_chars=4000 if empty_index else 0,
    ))

    assert observed == []
    assert result.answer == "现有资料中没有可用于回答的片段，请补充资料后再试。"
    assert result.sources == []
    assert result.invalid_ids == []
    assert result.response is None


def test_rag_chain_reports_blank_answer_and_keeps_actual_response(
    seeded_index, offline_rag
):
    """已经调用模型却得到空白正文时，报告失败并保留真实响应和usage。"""
    run, observed = offline_rag

    with pytest.raises(langchain_rag.LangChainRagAnswerError) as error_info:
        asyncio.run(run(seeded_index, " \n ", max_chars=250))

    assert len(observed) == 1
    assert error_info.value.response.content == " \n "
    assert error_info.value.response.usage_metadata["total_tokens"] == 12
