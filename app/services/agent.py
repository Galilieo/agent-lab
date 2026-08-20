from dataclasses import dataclass

from app.services.llm import LLMResult, generate_reply
from app.tools import CALCULATOR_TOOL, execute_tool


@dataclass
class AgentResult:
    answer: str | None
    model_calls: list[LLMResult]


async def run_agent(
    message: str,
    history: list[dict[str, str]] | None = None,
) -> AgentResult:
    first_result = await generate_reply(
        message=message,
        history=history,
        tools=[CALCULATOR_TOOL],
    )

    if not first_result.tool_calls:
        return AgentResult(
            answer=first_result.answer,
            model_calls=[first_result],
        )

    assistant_tool_calls = []
    tool_messages = []

    for tool_call in first_result.tool_calls:
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

    additional_messages = [
        {
            "role": "assistant",
            "content": first_result.answer,
            "tool_calls": assistant_tool_calls,
        },
        *tool_messages,
    ]

    final_result = await generate_reply(
        message=message,
        history=history,
        additional_messages=additional_messages,
    )
    return AgentResult(
        answer=final_result.answer,
        model_calls=[
            first_result,
            final_result,
        ],
    )
