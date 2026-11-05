"""复用模型/计算器节点，在工具执行前请求调用方确认。

独立教学图通过interrupt交出待确认工具信息，调用方以Command恢复。
本层不提供UI或身份校验；拒绝时结束图，保留真实调用，不虚构最终模型回答。
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from app.services.langgraph_agent import (
    CalculatorState,
    call_model,
    call_tools,
    choose_next,
)


class ApprovalCalculatorState(CalculatorState):
    """继承原图数据和列表合并规则，额外保留最近一次人工决定。"""

    tool_approved: bool | None


def request_tool_approval(state: ApprovalCalculatorState) -> dict:
    """展示最新工具请求并暂停；恢复后严格接收布尔决定，提交状态更新。

    本节点只整理信息，不执行工具；interrupt前的代码在恢复时会重新执行。
    """
    latest = state["model_calls"][-1]

    decision = interrupt({
        "question": "是否允许执行本次工具请求？",
        "tool_calls": [{
            "call_id": call.call_id,
            "name": call.name,
            "arguments": call.arguments,
        } for call in latest.tool_calls],
    })

    if not isinstance(decision, bool):
        raise ValueError("Approval decision must be a boolean.")

    return {"tool_approved": decision}


def choose_after_approval(state: ApprovalCalculatorState) -> str:
    """同意进入use_tools，拒绝映射finish；不修改状态或请求模型。"""
    if state["tool_approved"] is True:
        return "use_tools"

    return "finish"


def build_approval_calculator_graph(
    *,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """编译带人工确认的独立图，调用方持有存储并负责发送恢复输入。

    模型后先复用工具请求/预算判断，再进入approval；同意才走tools。
    返回原始图状态，暂停及拒绝均不转换为正常回答的AgentResult。
    """
    if checkpointer is None:
        raise ValueError("Approval graph requires a checkpointer.")
    builder = StateGraph(ApprovalCalculatorState)
    builder.add_node("model", call_model)
    builder.add_node("approval", request_tool_approval)
    builder.add_node("tools", call_tools)
    builder.add_edge(START, "model")
    builder.add_conditional_edges(
        "model", choose_next, {"use_tools": "approval", "finish": END},
    )
    builder.add_conditional_edges(
        "approval", choose_after_approval, {"use_tools": "tools", "finish": END},
    )
    builder.add_edge("tools", "model")
    return builder.compile(checkpointer=checkpointer)
