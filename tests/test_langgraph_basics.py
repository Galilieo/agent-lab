"""对教学文本图运行真实LangGraph，检查状态传递而非业务问答效果。

节点只处理字符串；预期结果保护部分更新、顺序边和trace追加规则。
不使用fake模型或客户端，不验证模型/工具/HTTP接线。
"""

from copy import deepcopy

from app.services.langgraph_basics import build_preview_graph


def test_preview_graph_preserves_question_and_appends_step_updates():
    """后节点使用前节点的新状态，未更新字段保留，reducer只追加本步轨迹。"""
    initial = {
        "question": "  计算2+3  ",
        "normalized_question": "",
        "preview": "",
        "trace": ["input"],
    }
    original = deepcopy(initial)
    graph = build_preview_graph()

    result = graph.invoke(initial)

    assert result == {
        "question": "  计算2+3  ",
        "normalized_question": "计算2+3",
        "preview": "预览：计算2+3",
        "trace": ["input", "prepare_question", "render_preview"],
    }
    assert initial == original
