"""验证记忆提取的本地触发规则，不调用 LLM 或写入数据库。

用同一个测试比较显式保存、普通提问、混合临时/长期意图和不保存要求。
触发表示值得进一步提取，不等于可以直接持久化。
"""

import pytest

from app.services import memory


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("记住，以后默认用中文回答。", True),
        ("解释一下 Python 装饰器。", False),
        # 临时要求与长期偏好可以同时出现，不能看到“这次”就整条拒绝。
        ("这次详细一点，以后默认简洁一些。", True),
        # 明确不保存本条消息，应优先于其中的学习目标线索。
        ("不要保存这条消息，我的学习目标是开发 Agent。", False),
    ],
    ids=["explicit-save", "ordinary-question", "mixed-intents", "do-not-save"],
)
def test_should_extract_memory_respects_intent_priority(message, expected):
    """比较预筛选结果，保护不保存优先与长期意图不被临时词误伤的规则。"""
    actual = memory.should_extract_memory(message)

    # 严格检查布尔返回值，避免把 1、0 等相等但类型不同的值视为通过。
    assert actual is expected
