"""原生 Agent 编排层：反复调用模型、执行工具并回传结果。

由 /chat 调用，依赖 llm 完成单次模型请求。这里只管理模型与工具循环，
不直接处理 HTTP 响应或提交数据库；通过结果和异常携带调用记录交给路由保存。
"""

from dataclasses import dataclass

from app.services.llm import (
    LLMRequestError,
    LLMResult,
    generate_reply,
)
from app.services.mcp_tools import execute_mcp_notes
from app.tools import AVAILABLE_TOOLS, execute_tool


# 限制模型请求次数，不是工具数量；一次模型响应可能请求多个工具。
DEFAULT_MAX_MODEL_CALLS = 3


@dataclass
class AgentResult:
    """把最终回答与整轮成功模型调用一起交回路由，避免丢失中间调用。"""
    answer: str | None
    model_calls: list[LLMResult]


class AgentRunError(Exception):
    """后续模型请求失败时，携带原始错误和此前已经成功的调用。"""

    def __init__(
        self,
        cause: LLMRequestError,
        completed_model_calls: list[LLMResult],
    ) -> None:
        super().__init__(str(cause))
        self.cause = cause
        self.completed_model_calls = completed_model_calls


class AgentModelCallLimitError(Exception):
    """模型调用预算耗尽；携带预算内的成功调用，不虚构失败模型请求。"""

    def __init__(
        self,
        completed_model_calls: list[LLMResult],
    ) -> None:
        super().__init__(
            "Agent reached the maximum number of model calls."
        )
        self.completed_model_calls = completed_model_calls


class AgentToolError(Exception):
    """工具校验、分发或执行失败；保留原始原因和此前成功模型调用。"""

    def __init__(
        self,
        cause: Exception,
        completed_model_calls: list[LLMResult],
    ) -> None:
        super().__init__("Agent tool execution failed.")
        self.cause = cause
        self.completed_model_calls = completed_model_calls


async def run_agent(
    message: str,
    history: list[dict[str, str]] | None = None,
    max_model_calls: int = DEFAULT_MAX_MODEL_CALLS,
) -> AgentResult:
    """循环请求模型，直到获得最终回答或触发预算、模型、工具失败边界。

    Args:
        message: 本轮用户问题；每次模型请求只加入一次，不重复进入旧历史。
        history: 数据库恢复的历史消息，不包含本轮用户消息。
        max_model_calls: 整轮最多请求模型的次数，包括最终回答调用。

    Returns:
        最终回答及全部成功的模型调用记录。工具请求与结果仅在本轮累积。

    Raises:
        ValueError: 模型调用预算小于 1。
        LLMRequestError: 第一次模型调用直接失败。
        AgentRunError: 已有成功调用后，后续模型调用失败。
        AgentModelCallLimitError: 已用尽模型调用预算但还没有最终回答。
        AgentToolError: 工具处理失败。
    """
    if max_model_calls < 1:
        raise ValueError("max_model_calls must be greater than 0")

    model_calls: list[LLMResult] = []
    additional_messages: list[dict] = []

    for _ in range(max_model_calls):
        try:
            result = await generate_reply(
                message=message,
                history=history,
                tools=AVAILABLE_TOOLS,
                additional_messages=additional_messages,
            )
        except LLMRequestError as exc:
            if not model_calls:
                raise

            # 用列表快照携带已完成调用，路由才能在整轮失败后仍保存真实调用轨迹。
            raise AgentRunError(
                cause=exc,
                completed_model_calls=model_calls.copy(),
            ) from exc

        model_calls.append(result)

        if not result.tool_calls:
            return AgentResult(
                answer=result.answer,
                model_calls=model_calls,
            )

        # 没有下一次模型调用预算时，先停止，避免再执行无法交回模型的工具动作。
        if len(model_calls) == max_model_calls:
            raise AgentModelCallLimitError(
                completed_model_calls=model_calls.copy(),
            )

        assistant_tool_calls = []
        tool_messages = []

        for tool_call in result.tool_calls:
            assistant_tool_calls.append(
                {
                    "id": tool_call.call_id,
                    "type": "function",
                    "function": {
                        "name": tool_call.name,
                        "arguments": tool_call.arguments,
                    },
                }
            )

            try:
                # 笔记查询经 MCP Server 执行，其他工具继续在当前进程直接执行。
                if tool_call.name == "search_notes":
                    tool_result = await execute_mcp_notes(tool_call)
                else:
                    tool_result = execute_tool(tool_call)
            except Exception as exc:
                raise AgentToolError(
                    cause=exc,
                    completed_model_calls=model_calls.copy(),
                ) from exc

            # tool_call_id 必须对应模型原请求的 id，模型才能识别结果属于哪个工具请求。
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.call_id,
                    "content": tool_result,
                }
            )

        # 先保留 assistant 的工具请求，再追加 tool 结果，供下一轮模型一起读取。
        additional_messages.extend(
            [
                {
                    "role": "assistant",
                    "content": result.answer,
                    "tool_calls": assistant_tool_calls,
                },
                *tool_messages,
            ]
        )
