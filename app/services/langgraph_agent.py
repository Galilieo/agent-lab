"""用状态图编排单次模型调用与计算器，复用项目结果和异常契约。

模型节点提交调用记录，工具节点提交交互消息，条件边决定继续或结束。
仅提供计算器；可接收调用方提供的检查点组件，不管理其连接。
不接入HTTP路由、记忆/检索或业务数据库，不在这里执行流式输出。
"""

from operator import add
from typing import Annotated, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.services.agent import (
    AGENT_SYSTEM_PROMPT,
    DEFAULT_MAX_MODEL_CALLS,
    AgentModelCallLimitError,
    AgentResult,
    AgentRunError,
    AgentToolError,
)
from app.services.langchain_adapter import generate_langchain_result
from app.services.langgraph_checkpoint import create_checkpoint_serializer
from app.services.llm import LLMRequestError, LLMResult
from app.tools import CALCULATOR_TOOL, execute_tool


class CalculatorState(TypedDict):
    """入口初始化全部字段；节点只返回本步新增调用或交互消息。"""

    question: str
    history: list[dict[str, str]]
    additional_messages: Annotated[list[dict], add]
    model_calls: Annotated[list[LLMResult], add]
    max_model_calls: int


def _execute_calculator_requests(result: LLMResult) -> list[dict]:
    """执行本次原始工具请求，构造下一轮所需的assistant/tool消息。

    参数解析与计算复用execute_tool，保留原始arguments及call_id。
    未知工具或执行错误向上抛出，由工具节点携带已有调用记录。
    """
    requests = [{
        "id": call.call_id, "type": "function",
        "function": {"name": call.name, "arguments": call.arguments},
    } for call in result.tool_calls]
    tool_messages = []
    for call in result.tool_calls:
        if call.name != "calculator":
            raise ValueError("Only calculator is enabled for this graph.")
        content = execute_tool(call)
        tool_messages.append({
            "role": "tool", "tool_call_id": call.call_id, "content": content,
        })
    return [{
        "role": "assistant", "content": result.answer, "tool_calls": requests,
    }, *tool_messages]


async def call_model(state: CalculatorState) -> dict:
    """请求模型，提交本次新增调用，失败时保留既有记录。"""
    try:
        result = await generate_langchain_result(
            message=state["question"],
            history=state["history"],
            tools=[CALCULATOR_TOOL],
            additional_messages=state["additional_messages"],
            system_prompt=AGENT_SYSTEM_PROMPT,
        )
    except LLMRequestError as exc:
        if not state["model_calls"]:
            raise

        raise AgentRunError(
            cause=exc,
            completed_model_calls=state["model_calls"].copy(),
        ) from exc

    return {"model_calls": [result]}


def call_tools(state: CalculatorState) -> dict:
    """执行最新响应的计算器请求，返回新增交互；工具失败时保留真实模型调用。"""
    try:
        messages = _execute_calculator_requests(
            state["model_calls"][-1],
        )
    except Exception as exc:
        raise AgentToolError(
            cause=exc,
            completed_model_calls=state["model_calls"].copy(),
        ) from exc

    return {"additional_messages": messages}


def choose_next(state: CalculatorState) -> str:
    """无工具请求时finish，有请求且预算允许时use_tools；耗尽则执行工具前抛错。"""
    latest = state["model_calls"][-1]

    if not latest.tool_calls:
        return "finish"

    if len(state["model_calls"]) >= state["max_model_calls"]:
        raise AgentModelCallLimitError(
            completed_model_calls=state["model_calls"].copy(),
        )

    return "use_tools"


def create_calculator_checkpointer() -> InMemorySaver:
    """创建由调用方复用的内存存取组件，明确支持本图的自定义记录类型。

    序列化保存字段，反序列化还原LLMResult及其嵌套LLMToolCall。
    这里只在内存保存检查点，不连接业务SQLite；新实例不共享旧实例的数据。
    """
    return InMemorySaver(serde=create_checkpoint_serializer())


def build_calculator_graph(
    *,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """编译模型/工具循环，可由调用方提供检查点组件保存流程状态。"""
    builder = StateGraph(CalculatorState)
    builder.add_node("model", call_model)
    builder.add_node("tools", call_tools)

    builder.add_edge(START, "model")
    builder.add_conditional_edges(
        "model",
        choose_next,
        {"use_tools": "tools", "finish": END},
    )
    builder.add_edge("tools", "model")

    return builder.compile(checkpointer=checkpointer)


async def run_calculator_graph(
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    max_model_calls: int = DEFAULT_MAX_MODEL_CALLS,
) -> AgentResult:
    """初始化独立状态并运行图，正常结束后映射成项目AgentResult。

    模型次数预算由路由检查；图步数上限只作调度保护，两者不是同一计数。
    模型/工具异常由节点携带已有记录向外传播，本层不虚构失败调用或写入数据库。
    """
    if max_model_calls < 1:
        raise ValueError("max_model_calls must be greater than 0")
    graph = build_calculator_graph()
    final = await graph.ainvoke({
        "question": message,
        "history": list(history or []),
        "additional_messages": [],
        "model_calls": [],
        "max_model_calls": max_model_calls,
    }, config={"recursion_limit": 2 * max_model_calls + 1})
    calls = final["model_calls"]
    return AgentResult(answer=calls[-1].answer, model_calls=calls)
