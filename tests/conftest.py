"""隔离 HTTP 路由中的自动记忆提取，防止旧测试新增真实模型请求。

默认让路由提取入口返回 skip，接线测试按场景覆盖该入口。
不替换服务层 extract_memories，直接服务测试仍用各自的 fake HTTP 验证解析。
"""

import pytest

from app.schemas import MemoryExtractionResult


@pytest.fixture(autouse=True)
def isolate_chat_memory_extraction(monkeypatch):
    """只替换路由使用的提取引用，保留其他本地代码真实执行。"""
    async def skip_extraction(message):
        return MemoryExtractionResult(action="skip")

    # 路由引用在接线 RED 阶段尚未导入，允许先提供测试替身。
    monkeypatch.setattr("app.main.extract_memories", skip_extraction, raising=False)
