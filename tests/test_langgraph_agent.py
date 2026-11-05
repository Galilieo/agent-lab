"""真实LangGraph、框架模型适配和计算器，外部模型HTTP使用预设响应。

验证条件分支、工具循环、预算、检查点、人工确认及模型失败恢复，SQLite用临时文件。
不证明真实模型工具选择、进程重启恢复或身份权限。
"""

import asyncio
import json

import httpx
import pytest
from langgraph.types import Command

from app.services import (
    langchain_adapter,
    langgraph_agent,
    langgraph_approval,
    langgraph_checkpoint,
)
from app.services.agent import (
    AgentModelCallLimitError,
    AgentResult,
    AgentRunError,
    AgentToolError,
)
from app.services.llm import LLMResult, LLMTimeoutError, LLMToolCall


@pytest.fixture
def offline_graph(monkeypatch):
    """只替换HTTP传输，工具入口用观察包装保留真实执行与校验。"""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setattr(langchain_adapter.settings, "openai_api_key", "offline-placeholder")
    monkeypatch.setattr(langchain_adapter.settings, "openai_base_url", "https://example.invalid/v1")
    monkeypatch.setattr(langchain_adapter.settings, "openai_model", "offline-model")
    observed = {"requests": [], "tool_attempts": []}
    real_execute = langgraph_agent.execute_tool

    def observed_execute(call):
        observed["tool_attempts"].append(call.call_id)
        return real_execute(call)

    monkeypatch.setattr(langgraph_agent, "execute_tool", observed_execute)

    def prepare(messages):
        pending = iter(messages)

        def respond(request):
            observed["requests"].append(json.loads(request.content))
            message = next(pending)
            if message == "timeout":
                raise httpx.ReadTimeout("offline timeout", request=request)
            return httpx.Response(200, json={
                "id": "offline-graph", "object": "chat.completion", "created": 0,
                "model": "offline-model",
                "choices": [{
                    "index": 0,
                    "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
                    "message": message,
                }],
                "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
            })

        def create_client(**kwargs):
            return httpx.AsyncClient(**kwargs, transport=httpx.MockTransport(respond))

        monkeypatch.setattr(langchain_adapter, "AsyncClient", create_client)

    return prepare, observed


def calculator_request(arguments='{"left":2,"operator":"+","right":3}'):
    """预设模型请求，参数字符串原样经过模型适配再交工具校验。"""
    return {
        "role": "assistant", "content": None,
        "tool_calls": [{
            "id": "call_graph", "type": "function",
            "function": {"name": "calculator", "arguments": arguments},
        }],
    }


@pytest.mark.parametrize("use_tool", [False, True], ids=["direct", "calculator"])
def test_graph_routes_to_end_or_calculator_and_preserves_calls(offline_graph, use_tool):
    """同图直接结束或真实计算后回模型；每个节点只提交新增调用/消息。"""
    prepare, observed = offline_graph
    responses = [calculator_request()] if use_tool else []
    responses.append({"role": "assistant", "content": "结果是5。"})
    prepare(responses)
    history = [{"role": "assistant", "content": "继续。"}]

    result = asyncio.run(langgraph_agent.run_calculator_graph("计算2+3", history))

    assert isinstance(result, AgentResult)
    assert result.answer == "结果是5。"
    assert len(result.model_calls) == len(observed["requests"]) == (2 if use_tool else 1)
    assert observed["tool_attempts"] == (["call_graph"] if use_tool else [])
    for call, payload in zip(result.model_calls, observed["requests"]):
        assert call.upstream_status == 200
        assert call.total_tokens == 12
        assert [tool["function"]["name"] for tool in payload["tools"]] == ["calculator"]
        assert payload["messages"][1:3] == [
            {"role": "assistant", "content": "继续。"},
            {"role": "user", "content": "计算2+3"},
        ]
    if use_tool:
        assert result.model_calls[0].tool_calls[0].call_id == "call_graph"
        sent = observed["requests"][1]["messages"]
        assert [message["role"] for message in sent] == ["system", "assistant", "user", "assistant", "tool"]
        assert sent[-2]["tool_calls"][0]["id"] == "call_graph"
        assert sent[-1] == {"role": "tool", "tool_call_id": "call_graph", "content": "5"}
    assert history == [{"role": "assistant", "content": "继续。"}]


@pytest.mark.parametrize("failure", ["timeout", "bad-arguments", "budget"])
def test_graph_preserves_calls_and_checks_budget_before_tools(offline_graph, failure):
    """模型失败/工具失败保留已发生调用；最后一次模型预算后不执行工具。"""
    prepare, observed = offline_graph
    if failure == "timeout":
        messages = [calculator_request(), "timeout"]
        expected = AgentRunError
    elif failure == "bad-arguments":
        messages = [calculator_request("{bad json")]
        expected = AgentToolError
    else:
        messages = [calculator_request()]
        expected = AgentModelCallLimitError
    prepare(messages)

    with pytest.raises(expected) as caught:
        asyncio.run(langgraph_agent.run_calculator_graph(
            "计算2+3", max_model_calls=1 if failure == "budget" else 3,
        ))

    assert len(caught.value.completed_model_calls) == 1
    completed = caught.value.completed_model_calls[0]
    assert completed.upstream_status == 200
    assert completed.total_tokens == 12
    assert completed.tool_calls[0].call_id == "call_graph"
    if failure == "timeout":
        assert len(observed["requests"]) == 2
        assert observed["tool_attempts"] == ["call_graph"]
        assert isinstance(caught.value.cause, LLMTimeoutError)
    elif failure == "bad-arguments":
        assert len(observed["requests"]) == 1
        assert observed["tool_attempts"] == ["call_graph"]
        assert isinstance(caught.value.cause, json.JSONDecodeError)
    else:
        assert len(observed["requests"]) == 1
        assert observed["tool_attempts"] == []


def test_checkpoint_reads_saved_calls_and_isolates_independent_tasks(offline_graph):
    """同存储重建图可读回真实记录；新任务隔离，读取和结束后继续不重跑模型。"""
    prepare, observed = offline_graph
    prepare([
        calculator_request(),
        {"role": "assistant", "content": "任务A：结果是5。"},
        {"role": "assistant", "content": "任务B：你好。"},
    ])

    async def scenario():
        saver = langgraph_agent.create_calculator_checkpointer()
        graph = langgraph_agent.build_calculator_graph(checkpointer=saver)
        config_a = {"configurable": {"thread_id": "calculator-task-A"}}
        config_b = {"configurable": {"thread_id": "calculator-task-B"}}

        await graph.ainvoke({
            "question": "计算2+3", "history": [],
            "additional_messages": [], "model_calls": [], "max_model_calls": 3,
        }, config=config_a)
        assert len(observed["requests"]) == 2

        # 换编译图但复用同一个saver，检查数据来自检查点存取而非返回值变量。
        rebuilt = langgraph_agent.build_calculator_graph(checkpointer=saver)
        snapshot_a = await rebuilt.aget_state(config_a)
        calls = snapshot_a.values["model_calls"]
        assert snapshot_a.values["question"] == "计算2+3"
        assert snapshot_a.next == ()
        assert len(calls) == 2
        assert all(isinstance(call, LLMResult) for call in calls)
        assert isinstance(calls[0].tool_calls[0], LLMToolCall)
        assert calls[0].tool_calls[0].call_id == "call_graph"
        assert calls[0].tool_calls[0].arguments == '{"left":2,"operator":"+","right":3}'
        assert calls[-1].answer == "任务A：结果是5。"
        assert snapshot_a.values["additional_messages"][-1] == {
            "role": "tool", "tool_call_id": "call_graph", "content": "5",
        }
        assert len(observed["requests"]) == 2

        # 正常结束的任务没有待执行节点；None继续只返回已有结果。
        finished = await rebuilt.ainvoke(None, config=config_a)
        assert finished["model_calls"][-1].answer == "任务A：结果是5。"
        assert len(observed["requests"]) == 2

        before_b = await rebuilt.aget_state(config_b)
        assert before_b.values == {}
        await rebuilt.ainvoke({
            "question": "你好", "history": [],
            "additional_messages": [], "model_calls": [], "max_model_calls": 3,
        }, config=config_b)
        snapshot_b = await rebuilt.aget_state(config_b)
        assert snapshot_b.values["question"] == "你好"
        assert len(snapshot_b.values["model_calls"]) == 1
        assert snapshot_b.values["model_calls"][0].answer == "任务B：你好。"
        after_b = await rebuilt.aget_state(config_a)
        assert after_b.values == snapshot_a.values
        assert len(observed["requests"]) == 3
        assert observed["tool_attempts"] == ["call_graph"]

        # 即使任务编号相同，新的内存saver也没有原实例的检查点。
        empty_graph = langgraph_agent.build_calculator_graph(
            checkpointer=langgraph_agent.create_calculator_checkpointer(),
        )
        missing = await empty_graph.aget_state(config_a)
        assert missing.values == {}
        assert len(observed["requests"]) == 3

    asyncio.run(scenario())


def test_sqlite_checkpoint_survives_connection_reopen(offline_graph, tmp_path):
    """真实临时文件关闭后用新连接读回；读取不请求模型，其他任务仍隔离。"""
    prepare, observed = offline_graph
    prepare([
        calculator_request(),
        {"role": "assistant", "content": "结果是5。"},
    ])
    database_path = tmp_path / "graph-checkpoints.sqlite3"

    async def scenario():
        config = {"configurable": {"thread_id": "persistent-task-A"}}
        async with langgraph_checkpoint.open_calculator_checkpointer(
            str(database_path),
        ) as first_saver:
            graph = langgraph_agent.build_calculator_graph(checkpointer=first_saver)
            await graph.ainvoke({
                "question": "计算2+3", "history": [],
                "additional_messages": [], "model_calls": [], "max_model_calls": 3,
            }, config=config)
            before = await graph.aget_state(config)

        # 退出第一个上下文后，重新打开相同文件，不复用旧连接或旧saver。
        assert database_path.is_file()
        async with langgraph_checkpoint.open_calculator_checkpointer(
            str(database_path),
        ) as second_saver:
            assert second_saver is not first_saver
            assert second_saver.conn is not first_saver.conn
            rebuilt = langgraph_agent.build_calculator_graph(checkpointer=second_saver)
            after = await rebuilt.aget_state(config)
            assert after.values == before.values
            assert after.next == ()
            assert after.values["question"] == "计算2+3"
            calls = after.values["model_calls"]
            assert len(calls) == 2
            assert isinstance(calls[0], LLMResult)
            assert isinstance(calls[0].tool_calls[0], LLMToolCall)
            assert calls[0].tool_calls[0].call_id == "call_graph"
            assert calls[-1].answer == "结果是5。"
            missing = await rebuilt.aget_state({
                "configurable": {"thread_id": "independent-task-B"},
            })
            assert missing.values == {}

        assert len(observed["requests"]) == 2
        assert observed["tool_attempts"] == ["call_graph"]

    asyncio.run(scenario())


@pytest.mark.parametrize("approved", [True, False], ids=["approve", "reject"])
def test_approval_pauses_before_tools_and_resumes_after_reopen(
    offline_graph, tmp_path, monkeypatch, approved,
):
    """暂停后重开SQLite，同意才执行一次工具，拒绝不执行且保留成功模型记录。"""
    prepare, observed = offline_graph
    responses = [calculator_request()]
    if approved:
        responses.append({"role": "assistant", "content": "结果是5。"})
    prepare(responses)
    database_path = str(tmp_path / "approval-checkpoints.sqlite3")
    approval_entries = []
    real_approval = langgraph_approval.request_tool_approval

    def observed_approval(state):
        approval_entries.append("entered")
        return real_approval(state)

    monkeypatch.setattr(langgraph_approval, "request_tool_approval", observed_approval)

    async def scenario():
        config = {"configurable": {"thread_id": "approval-task-A"}}
        async with langgraph_checkpoint.open_calculator_checkpointer(
            database_path,
        ) as first_saver:
            graph = langgraph_approval.build_approval_calculator_graph(
                checkpointer=first_saver,
            )
            paused = await graph.ainvoke({
                "question": "计算2+3", "history": [],
                "additional_messages": [], "model_calls": [],
                "max_model_calls": 3, "tool_approved": None,
            }, config=config)
            assert len(paused["__interrupt__"]) == 1
            assert paused["__interrupt__"][0].value == {
                "question": "是否允许执行本次工具请求？",
                "tool_calls": [{
                    "call_id": "call_graph", "name": "calculator",
                    "arguments": '{"left":2,"operator":"+","right":3}',
                }],
            }
            pending = await graph.aget_state(config)
            assert pending.next == ("approval",)
            assert pending.values["tool_approved"] is None
            assert len(pending.values["model_calls"]) == 1
            assert pending.values["additional_messages"] == []
            assert len(observed["requests"]) == 1
            assert observed["tool_attempts"] == []
            assert len(approval_entries) == 1

        # 恢复时换连接与编译图，但保持数据库文件和任务编号相同。
        async with langgraph_checkpoint.open_calculator_checkpointer(
            database_path,
        ) as second_saver:
            rebuilt = langgraph_approval.build_approval_calculator_graph(
                checkpointer=second_saver,
            )
            final = await rebuilt.ainvoke(Command(resume=approved), config=config)
            snapshot = await rebuilt.aget_state(config)
            assert snapshot.next == ()
            assert final["tool_approved"] is approved
            assert len(approval_entries) == 2
            assert len(final["model_calls"]) == (2 if approved else 1)
            assert len(observed["requests"]) == (2 if approved else 1)
            assert observed["tool_attempts"] == (["call_graph"] if approved else [])
            if approved:
                assert final["model_calls"][-1].answer == "结果是5。"
                assert observed["requests"][-1]["messages"][-1] == {
                    "role": "tool", "tool_call_id": "call_graph", "content": "5",
                }
            else:
                assert final["additional_messages"] == []
                assert final["model_calls"][0].answer is None
                assert final["model_calls"][0].tool_calls[0].call_id == "call_graph"

    asyncio.run(scenario())


def test_model_timeout_resumes_saved_tool_result_after_reopen(offline_graph, tmp_path):
    """后续模型超时后重开SQLite继续，复用已保存计算结果，只重试失败模型步骤。"""
    prepare, observed = offline_graph
    prepare([
        calculator_request(),
        "timeout",
        {"role": "assistant", "content": "恢复后结果是5。"},
    ])
    database_path = str(tmp_path / "recovery-checkpoints.sqlite3")

    async def scenario():
        config = {"configurable": {"thread_id": "recover-model-task-A"}}
        async with langgraph_checkpoint.open_calculator_checkpointer(
            database_path,
        ) as first_saver:
            graph = langgraph_agent.build_calculator_graph(checkpointer=first_saver)
            with pytest.raises(AgentRunError) as caught:
                await graph.ainvoke({
                    "question": "计算2+3", "history": [],
                    "additional_messages": [], "model_calls": [], "max_model_calls": 3,
                }, config=config)

            assert isinstance(caught.value.cause, LLMTimeoutError)
            failed = await graph.aget_state(config)
            assert failed.next == ("model",)
            assert len(failed.values["model_calls"]) == 1
            assert caught.value.completed_model_calls == failed.values["model_calls"]
            assert failed.values["additional_messages"][-1] == {
                "role": "tool", "tool_call_id": "call_graph", "content": "5",
            }
            assert len(observed["requests"]) == 2
            assert observed["tool_attempts"] == ["call_graph"]

        # 不提交新输入或历史checkpoint_id；重开原文件，使用原任务编号继续。
        async with langgraph_checkpoint.open_calculator_checkpointer(
            database_path,
        ) as second_saver:
            rebuilt = langgraph_agent.build_calculator_graph(checkpointer=second_saver)
            pending = await rebuilt.aget_state(config)
            assert pending.values == failed.values
            assert pending.next == ("model",)
            assert len(observed["requests"]) == 2

            final = await rebuilt.ainvoke(None, config=config)
            completed = await rebuilt.aget_state(config)
            assert completed.next == ()
            assert final["model_calls"][-1].answer == "恢复后结果是5。"
            assert len(final["model_calls"]) == 2
            assert final["model_calls"][0] == failed.values["model_calls"][0]
            assert final["additional_messages"] == failed.values["additional_messages"]
            assert len(observed["requests"]) == 3
            assert observed["tool_attempts"] == ["call_graph"]
            assert observed["requests"][2]["messages"] == observed["requests"][1]["messages"]

    asyncio.run(scenario())
