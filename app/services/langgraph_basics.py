"""教学用的本地文本流程，观察节点间状态传递和列表合并规则。

清理节点派生去除两端空白的问题，预览节点读取该字段并拼接展示文本。
“计算2+3”在此只是输入字符串，预览不是计算结果或模型回答。
本模块不承担问答业务，也不请求模型、执行工具或接入HTTP/数据库。
"""

from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph


class PreviewState(TypedDict):
    """调用方初始化原始/派生字段，节点返回更新后由图按字段规则合并。

    question用于保留输入作对照，normalized_question是清理后的字符串。
    preview只是本地输出示例；trace由节点手动提交步骤名称，并非框架自动日志。
    """

    question: str
    normalized_question: str
    preview: str
    trace: Annotated[list[str], add]


def prepare_question(state: PreviewState) -> dict:
    """教学节点：从原问题派生去除两端空白的字符串。

    按状态契约通过trace提交本步名称，追加由字段reducer负责。
    """
    return {
        "normalized_question": state["question"].strip(),
        "trace": ["prepare_question"],
    }


def render_preview(state: PreviewState) -> dict:
    """教学节点：拼接“预览：清理后的问题”，观察下游能否读取上游更新。

    输出是确定的字符串处理结果，不进行计算或模型生成。
    """
    return {
        "preview": f"预览：{state['normalized_question']}",
        "trace": ["render_preview"],
    }


def build_preview_graph() -> CompiledStateGraph:
    """注册并编译两节点顺序图，返回供调用方运行的流程对象。

    本函数只负责搭图；调用返回对象的invoke(initial)才执行节点并得到最终状态。
    """
    builder = StateGraph(PreviewState)

    builder.add_node("prepare_question", prepare_question)
    builder.add_node("render_preview", render_preview)

    builder.add_edge(START, "prepare_question")
    builder.add_edge("prepare_question", "render_preview")
    builder.add_edge("render_preview", END)

    return builder.compile()
