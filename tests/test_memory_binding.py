"""验证候选与请求上下文的绑定，以及匿名用户级候选的整批拒绝。

直接构造结构合法的候选，检查应用补齐的归属与来源；不使用模型或数据库。
来源 ID 在这里仅作为绑定数据，不证明该消息存在或归属正确，数据库层另有保护。
"""

from dataclasses import asdict

import pytest

from app.schemas import MemoryExtractionResult
from app.services import memory


@pytest.mark.parametrize(
    ("user_id", "candidates", "expected"),
    [
        (
            "user-001",
            [
                {"scope": "user", "key": "answer_language", "value": "中文"},
                {"scope": "conversation", "key": "answer_language", "value": "英文"},
            ],
            [
                {
                    "scope": "user",
                    "scope_id": "user-001",
                    "key": "answer_language",
                    "value": "中文",
                    "source_message_id": 42,
                },
                {
                    "scope": "conversation",
                    "scope_id": "conversation-A",
                    "key": "answer_language",
                    "value": "英文",
                    "source_message_id": 42,
                },
            ],
        ),
        (
            None,
            [
                {"scope": "conversation", "key": "answer_language", "value": "英文"},
            ],
            [
                {
                    "scope": "conversation",
                    "scope_id": "conversation-A",
                    "key": "answer_language",
                    "value": "英文",
                    "source_message_id": 42,
                },
            ],
        ),
    ],
    ids=["identified-mixed-scopes", "anonymous-conversation-only"],
)
def test_prepare_memory_writes_binds_request_context(user_id, candidates, expected):
    """同批不同 scope 分别绑定归属，所有来源相同；匿名会话级候选仍可通过。"""
    extraction = MemoryExtractionResult.model_validate(
        {"action": "upsert", "memories": candidates}
    )

    writes = memory.prepare_memory_writes(
        extraction,
        user_id=user_id,
        conversation_id="conversation-A",
        source_message_id=42,
    )

    # 完整比较两种归属和统一来源，避免只检查条数而漏掉错误的身份绑定。
    actual = [asdict(write) for write in writes]
    assert actual == expected


def test_prepare_memory_writes_rejects_anonymous_mixed_batch():
    """匿名批次中存在 user 候选时应抛异常，不能返回过滤后的部分成功结果。"""
    extraction = MemoryExtractionResult.model_validate(
        {
            "action": "upsert",
            "memories": [
                # 刻意将合法会话级候选放在前面，后面再出现不合法的用户级候选。
                {"scope": "conversation", "key": "answer_language", "value": "英文"},
                {"scope": "user", "key": "answer_language", "value": "中文"},
            ],
        }
    )

    def prepare_anonymous():
        return memory.prepare_memory_writes(
            extraction,
            user_id=None,
            conversation_id="conversation-A",
            source_message_id=42,
        )

    # 必须报告整批失败；返回过滤后的部分候选也应让测试失败。
    with pytest.raises(ValueError):
        prepare_anonymous()
