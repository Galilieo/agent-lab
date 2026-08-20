import asyncio

import httpx

from app.services.agent import run_agent


def test_run_agent_returns_final_answer_after_calculator_tool_call(
    monkeypatch,
) -> None:
    observed_payloads = []

    class AgentLoopAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            observed_payloads.append(json)

            if len(observed_payloads) == 1:
                return httpx.Response(
                    200,
                    request=httpx.Request("POST", url),
                    json={
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_001",
                                            "type": "function",
                                            "function": {
                                                "name": "calculator",
                                                "arguments": (
                                                    '{"left":2,'
                                                    '"operator":"+",'
                                                    '"right":3}'
                                                ),
                                            },
                                        }
                                    ],
                                }
                            }
                        ],
                    },
                )
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "2 + 3 = 5",
                            }
                        }
                    ],
                },
            )

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        AgentLoopAsyncClient,
    )

    result = asyncio.run(
        run_agent(message="计算2 + 3")
    )

    assert result.answer == "2 + 3 = 5"
    assert len(result.model_calls) == 2
    assert result.model_calls[0].answer is None
    assert result.model_calls[0].tool_calls[0].call_id == "call_001"
    assert result.model_calls[1].answer == "2 + 3 = 5"
    assert len(observed_payloads) == 2
    assert (
        observed_payloads[0]["tools"][0]["function"]["name"] == "calculator"
    )
    assert observed_payloads[1]["messages"][-2:] == [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {
                        "name": "calculator",
                        "arguments": (
                            '{"left":2,'
                            '"operator":"+",'
                            '"right":3}'
                        ),
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_001",
            "content": "5",
        },
    ]
