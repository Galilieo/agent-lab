from dataclasses import dataclass

from app.services.llm import (
    LLMRequestError,
    LLMResult,
    generate_reply,
)
from app.tools import CALCULATOR_TOOL, execute_tool


DEFAULT_MAX_MODEL_CALLS = 3


@dataclass
class AgentResult:
    answer: str | None
    model_calls: list[LLMResult]


class AgentRunError(Exception):
    def __init__(
        self,
        cause: LLMRequestError,
        completed_model_calls: list[LLMResult],
    ) -> None:
        super().__init__(str(cause))
        self.cause = cause
        self.completed_model_calls = completed_model_calls


class AgentModelCallLimitError(Exception):
    def __init__(
        self,
        completed_model_calls: list[LLMResult],
    ) -> None:
        super().__init__(
            "Agent reached the maximum number of model calls."
        )
        self.completed_model_calls = completed_model_calls


async def run_agent(
    message: str,
    history: list[dict[str, str]] | None = None,
    max_model_calls: int = DEFAULT_MAX_MODEL_CALLS,
) -> AgentResult:
    if max_model_calls < 1:
        raise ValueError("max_model_calls must be greater than 0")

    model_calls: list[LLMResult] = []
    additional_messages: list[dict] = []

    for _ in range(max_model_calls):
        try:
            result = await generate_reply(
                message=message,
                history=history,
                tools=[CALCULATOR_TOOL],
                additional_messages=additional_messages,
            )
        except LLMRequestError as exc:
            if not model_calls:
                raise

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

            tool_result = execute_tool(tool_call)

            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.call_id,
                    "content": tool_result,
                }
            )

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
