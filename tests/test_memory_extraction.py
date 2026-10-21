"""定义提取结果模型的预期行为：多条候选、skip 和无效结构拒绝。

只验证 Pydantic 数据契约，不调用 LLM、不写数据库；实现进度以正式路线为准。
MemoryCandidate 校验单条候选，MemoryExtractionResult 校验动作与列表的关联。
"""

import pytest
from pydantic import ValidationError

from app import schemas


def test_memory_extraction_result_accepts_upsert_and_skip():
    """验证多条候选完整保留、内容去首尾空白，以及 skip 归一化为空列表。"""
    # 故意在第一条 value 两侧保留空格，验证模型会去除首尾空白。
    payload = {
        "action": "upsert",
        "memories": [
            {
                "scope": "user",
                "key": "answer_language",
                "value": " 中文 ",
            },
            {
                "scope": "user",
                "key": "learning_goal",
                "value": "学习 AI Agent 开发",
            },
        ],
    }

    result = schemas.MemoryExtractionResult.model_validate(payload)
    skipped = schemas.MemoryExtractionResult.model_validate({"action": "skip"})

    expected = {
        "action": "upsert",
        "memories": [
            {
                "scope": "user",
                "key": "answer_language",
                "value": "中文",
            },
            {
                "scope": "user",
                "key": "learning_goal",
                "value": "学习 AI Agent 开发",
            },
        ],
    }

    # 比较完整结果，同时保护两条候选的字段、内容和顺序。
    assert result.model_dump() == expected

    # skip 是正常的无候选结果，省略 memories 时应得到空列表。
    assert skipped.action == "skip"
    assert skipped.memories == []


@pytest.mark.parametrize(
    "payload",
    [
        # upsert 必须提供至少一条候选，不能用空列表冒充 skip。
        {"action": "upsert", "memories": []},
        {
            "action": "upsert",
            "memories": [
                {
                    "scope": "user",
                    "key": "answer_language",
                    "value": "中文",
                    # 来源消息由应用绑定，不能由模型指定。
                    "source_message_id": 999,
                },
            ],
        },
    ],
    ids=["empty-upsert", "model-supplied-source"],
)
def test_memory_extraction_result_rejects_invalid_candidates(payload):
    """验证空 upsert 与模型指定来源 ID 都必须抛出结构校验异常。"""

    def validate_result():
        return schemas.MemoryExtractionResult.model_validate(payload)

    # 预期是结构校验失败；未抛异常或抛出其他异常，测试都应失败。
    with pytest.raises(ValidationError):
        validate_result()
