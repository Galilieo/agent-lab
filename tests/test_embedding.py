"""fake HTTP 验证本地嵌入服务契约；不会连接 Ollama 或云端模型。"""

import asyncio

import httpx
import pytest

from app.services import embedding


def install_fake_response(monkeypatch, payload):
    observed = []

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, *, json):
            observed.append((url, json))
            return httpx.Response(
                200, request=httpx.Request("POST", url), json=payload,
            )

    monkeypatch.setattr(embedding.httpx, "AsyncClient", FakeAsyncClient)
    return observed


def test_embed_texts_preserves_order_and_skips_empty_input(monkeypatch):
    vectors = [[1.0] + [0.0] * 1023, [0.0, 1.0] + [0.0] * 1022]
    observed = install_fake_response(monkeypatch, {"embeddings": vectors})

    assert asyncio.run(embedding.embed_texts([])) == []
    assert asyncio.run(embedding.embed_texts(["数据库事务", "会话记忆"])) == vectors
    assert observed == [
        (
            "http://127.0.0.1:11434/api/embed",
            {
                "model": "bge-m3:latest",
                "input": ["数据库事务", "会话记忆"],
                "truncate": False,
            },
        ),
    ]


def test_embed_texts_rejects_missing_vector_instead_of_misaligning_chunks(monkeypatch):
    install_fake_response(monkeypatch, {"embeddings": [[1.0] + [0.0] * 1023]})

    with pytest.raises(ValueError, match="Embedding count"):
        asyncio.run(embedding.embed_texts(["数据库事务", "会话记忆"]))
