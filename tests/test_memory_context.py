"""验证合并后的记忆选择与完整文本预算，不调用数据库或模型。

已用于 build_memory_context 的正确 RED → GREEN，
不证明 /chat 注入或真实模型对偏好优先级的遵循。
"""

import json

import pytest

from app.services import memory


def read_context(context):
    """读出约定的独立参考数据，避免把整个字符串当作事实集合。"""
    label, body = context.split("\n", 1)
    assert label == "Memory Context:"
    return json.loads(body)


def test_memory_context_selects_relevant_keys_without_mutating_input():
    """防止无关记忆全塞入上下文，或选择过程删改输入记忆。"""
    # 故意把普通记忆放在前面，输出应由明确的层级顺序决定。
    memories = {
        "tech_stack": "Java + Python",
        "learning_goal": "掌握 FastAPI",
        "explanation_style": "先讲原理",
        "answer_language": "中文",
        "unknown_key": "不应注入",
    }
    before = memories.copy()

    context = memory.build_memory_context(memories, "请用英文告诉我现在几点")
    assert read_context(context) == {
        "answer_language": "中文",
        "explanation_style": "先讲原理",
    }

    context = memory.build_memory_context(memories, "帮我安排 FASTAPI 学习计划")
    assert read_context(context) == {
        "answer_language": "中文",
        "explanation_style": "先讲原理",
        "learning_goal": "掌握 FastAPI",
        "tech_stack": "Java + Python",
    }

    context = memory.build_memory_context(
        memories, "帮我安排 FASTAPI 学习计划", max_regular_items=1,
    )
    assert read_context(context) == {
        "answer_language": "中文",
        "explanation_style": "先讲原理",
        "learning_goal": "掌握 FastAPI",
    }
    assert memory.build_memory_context({}, "学习计划") == ""
    assert memory.build_memory_context({"tech_stack": "Python"}, "现在几点") == ""
    assert memories == before


def test_memory_context_skips_whole_entries_and_counts_rendered_budget():
    """防止忽略封装开销、截断值或遇到放不下的条目就提前停止。"""
    memories = {
        "tech_stack": "Python",
        "learning_goal": "学" * 301,
        "explanation_style": "先讲原理，不要直接给答案。" * 10,
        "answer_language": '中"文\n回答',
    }
    before = memories.copy()
    # 手工给出最终文本；引号和换行的 JSON 转义也占预算。
    expected = 'Memory Context:\n{"answer_language": "中\\"文\\n回答", "tech_stack": "Python"}'
    budget = len(expected)

    context = memory.build_memory_context(
        memories, "Python 学习计划", max_chars=budget, max_regular_items=1,
    )
    assert read_context(context) == {
        "answer_language": '中"文\n回答',
        "tech_stack": "Python",
    }
    assert len(context) == budget
    # 少一个字符就不能装下 tech_stack，应整条跳过而不是截断。
    smaller = memory.build_memory_context(
        memories, "Python 学习计划", max_chars=budget - 1,
    )
    assert read_context(smaller) == {"answer_language": '中"文\n回答'}
    assert len(smaller) <= budget - 1

    # 单条超限与总预算超限不同；总空间足够也不能突破 value 上限。
    assert memory.build_memory_context(
        {"learning_goal": "学" * 301}, "学习计划",
    ) == ""
    assert memory.build_memory_context(memories, "Python 学习计划", max_chars=0) == ""
    with pytest.raises(ValueError):
        memory.build_memory_context(memories, "Python 学习计划", max_chars=-1)
    assert memories == before
