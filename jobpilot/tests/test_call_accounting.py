"""验证模型网关的额度、重试、JSON 修复和逐次记账。

上游用 httpx.MockTransport 模拟，openai SDK 和网关代码真实执行，
调用记录写入真实测试库，并用独立连接读回检查。
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from json import loads
from typing import Any
from unittest.mock import Mock
from uuid import UUID, uuid4

import httpx
import pytest
from openai import APIStatusError, APITimeoutError, AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobpilot.config import ModelPurpose, ModelSettings, settings
from jobpilot.db.models import AiRun, ModelCall, User
from jobpilot.services.llm_gateway import (
    BudgetExhaustedError,
    ModelBudget,
    request_completion,
)

Responder = Callable[[httpx.Request], httpx.Response]


@pytest.fixture
async def run(session_factory: async_sessionmaker[AsyncSession]) -> AiRun:
    """先提交一条运行：网关用独立事务登记调用，要求所属运行已经可见。"""
    async with session_factory.begin() as session:
        owner = User(email="gateway@example.invalid", hashed_password="test")
        session.add(owner)
        await session.flush()
        run = AiRun(user_id=owner.user_id, kind="tailor")
        session.add(run)
    return run


@pytest.fixture
def no_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """重试测试不需要真的等待。"""
    monkeypatch.setattr(settings, "model_retry_delay_seconds", 0)


@asynccontextmanager
async def fake_upstream(respond: Responder) -> AsyncIterator[AsyncOpenAI]:
    """返回一个真实的 SDK 客户端，但每个 HTTP 请求都交给 respond 处理。"""
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    async with AsyncOpenAI(api_key="test", http_client=http_client) as client:
        yield client


def completion_response(
    content: str = "test result",
    *,
    prompt_tokens: int = 12,
    completion_tokens: int = 3,
    response_id: str = "test",
) -> httpx.Response:
    """构造一个 HTTP 200 的 chat completion 响应。"""
    return httpx.Response(
        200,
        json={
            "id": response_id,
            "object": "chat.completion",
            "created": 0,
            "model": "test",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        },
    )


def error_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, json={"error": {"message": "test error"}})


async def send(
    session_factory: async_sessionmaker[AsyncSession],
    run: AiRun,
    client: AsyncOpenAI,
    **overrides: Any,
) -> ChatCompletion:
    """用常用默认参数调用网关，测试只写出与自己相关的参数。"""
    arguments: dict[str, Any] = {
        "purpose": "rewrite",
        "messages": [{"role": "user", "content": "test"}],
        "json_output": False,
        "budget": ModelBudget(remaining_calls=10, remaining_tokens=100_000),
    } | overrides
    return await request_completion(
        session_factory, run.user_id, run.run_id, client=client, **arguments
    )


async def calls_of(
    session_factory: async_sessionmaker[AsyncSession], run: AiRun
) -> list[ModelCall]:
    """用新连接读回该运行的全部调用记录，确认它们已独立提交。"""
    async with session_factory() as reader:
        query = select(ModelCall).where(ModelCall.run_id == run.run_id)
        return list((await reader.scalars(query)).all())


def outcomes_and_usage(
    calls: list[ModelCall],
) -> set[tuple[str, int | None, int | None]]:
    return {
        (call.outcome, call.prompt_tokens, call.completion_tokens) for call in calls
    }


# ---------- 记账：每次发送一行，发送前登记、结束后结算 ----------


@pytest.mark.parametrize(
    ("thinking", "json_output"),
    [(False, True), (True, False)],
    ids=["json-output", "thinking"],
)
async def test_each_request_has_a_durable_call(
    session_factory: async_sessionmaker[AsyncSession],
    run: AiRun,
    monkeypatch: pytest.MonkeyPatch,
    thinking: bool,
    json_output: bool,
) -> None:
    """发送时就能看到登记；成功、校验失败、超时及 HTTP 错误逐笔结算。"""
    monkeypatch.setattr(settings, "model_max_attempts", 1)
    monkeypatch.setattr(
        settings,
        "rewrite",
        ModelSettings(
            model_name="configured-test-model",
            thinking=thinking,
            temperature=0.2,
            max_tokens=1024,
        ),
    )
    seen_ids: list[UUID] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        # 请求参数按用途配置组装
        body = loads(request.content)
        assert body.get("max_tokens") == 1024
        assert body["model"] == "configured-test-model"
        if thinking:
            assert body["thinking"] == {"type": "enabled"}
            assert "temperature" not in body
        else:
            assert body["thinking"] == {"type": "disabled"}
            assert body["temperature"] == 0.2
        if json_output:
            assert body["response_format"] == {"type": "json_object"}
        else:
            assert "response_format" not in body

        # 请求到达上游时，登记行已提交且仍是 unknown
        async with session_factory() as reader:
            records = (await reader.scalars(select(ModelCall))).all()
            (current,) = [row for row in records if row.call_id not in seen_ids]
            assert current.run_id == run.run_id and current.user_id == run.user_id
            assert current.purpose == "rewrite" and current.model == body["model"]
            assert current.outcome == "unknown" and current.latency_ms is None
            assert current.prompt_tokens is None and current.completion_tokens is None
            seen_ids.append(current.call_id)

        if len(seen_ids) == 3:
            raise httpx.ReadTimeout("test timeout", request=request)
        if len(seen_ids) == 4:
            return error_response(503)
        return completion_response()

    def reject_output(response: ChatCompletion) -> None:
        raise ValueError("invalid model output")

    async with fake_upstream(respond) as client:
        budget = ModelBudget(remaining_calls=4, remaining_tokens=100_000)
        options = {"json_output": json_output, "budget": budget}
        # 业务事务最后回滚，调用记录仍应保留
        async with session_factory() as business:
            business.add(User(email="rollback@example.invalid", hashed_password="test"))
            await business.flush()
            response = await send(session_factory, run, client, **options)
            assert response.choices[0].message.content == "test result"
            with pytest.raises(ValueError, match="invalid model output"):
                await send(
                    session_factory, run, client, validate=reject_output, **options
                )
            with pytest.raises(APITimeoutError):
                await send(session_factory, run, client, **options)
            with pytest.raises(APIStatusError):
                await send(session_factory, run, client, **options)
            await business.rollback()

    rows = {call.call_id: call for call in await calls_of(session_factory, run)}
    assert len(rows) == len(seen_ids) == 4
    assert [rows[key].outcome for key in seen_ids] == [
        "success",
        "invalid_output",
        "unknown",
        "http_error",
    ]
    for key in seen_ids[:2]:
        assert (rows[key].prompt_tokens, rows[key].completion_tokens) == (12, 3)
    for key in seen_ids[2:]:
        assert rows[key].prompt_tokens is None and rows[key].completion_tokens is None
    assert all(row.latency_ms is not None for row in rows.values())


async def test_unknown_purpose_is_rejected_before_registration_and_send() -> None:
    """用途错误时，网关不会开启记账事务或调用模型客户端。"""
    session_factory = Mock(spec=async_sessionmaker)
    client = Mock(spec=AsyncOpenAI)

    with pytest.raises(ValueError, match="parse_jdd"):
        await request_completion(
            session_factory,
            uuid4(),
            uuid4(),
            client=client,
            purpose="parse_jdd",
            messages=[{"role": "user", "content": "test"}],
            json_output=True,
            budget=ModelBudget(remaining_calls=1, remaining_tokens=1024),
        )

    session_factory.begin.assert_not_called()
    client.with_options.assert_not_called()


@pytest.mark.parametrize("purpose", list(ModelPurpose))
def test_every_purpose_has_model_settings(purpose: ModelPurpose) -> None:
    """新增用途却漏加配置字段时，在测试阶段而不是首次调用时暴露。"""
    assert isinstance(settings.model_for_purpose(purpose), ModelSettings)


# ---------- 额度 ----------


def test_model_budget_allows_the_last_call() -> None:
    """余额恰好能覆盖一次发送时，可以用完最后一个名额。"""
    budget = ModelBudget(remaining_calls=1, remaining_tokens=100)

    budget.reserve(100)

    assert (budget.remaining_calls, budget.remaining_tokens) == (0, 0)
    with pytest.raises(BudgetExhaustedError, match="调用次数"):
        budget.reserve(1)


def test_token_budget_rejection_keeps_call_allowance() -> None:
    """token 不足时，两种余额都保持原值。"""
    budget = ModelBudget(remaining_calls=2, remaining_tokens=99)

    with pytest.raises(BudgetExhaustedError, match="token"):
        budget.reserve(100)

    assert (budget.remaining_calls, budget.remaining_tokens) == (2, 99)


@pytest.mark.usefixtures("no_retry_delay")
async def test_call_budget_blocks_retry_before_registration(
    session_factory: async_sessionmaker[AsyncSession],
    run: AiRun,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """首次超时用完调用名额，预算拒绝的重试不会发送或新增模型调用行。"""
    monkeypatch.setattr(settings, "model_max_attempts", 2)
    monkeypatch.setattr(settings, "rewrite", ModelSettings(max_tokens=64))
    budget = ModelBudget(remaining_calls=1, remaining_tokens=1024)
    sends = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal sends
        sends += 1
        raise httpx.ReadTimeout("test timeout", request=request)

    async with fake_upstream(respond) as client:
        with pytest.raises(BudgetExhaustedError, match="调用次数"):
            await send(session_factory, run, client, budget=budget)

    assert sends == 1
    assert budget.remaining_calls == 0
    calls = await calls_of(session_factory, run)
    assert outcomes_and_usage(calls) == {("unknown", None, None)}
    assert len(calls) == 1


# ---------- 重试：只重发超时、连接错误和 5xx ----------


@pytest.mark.usefixtures("no_retry_delay")
@pytest.mark.parametrize(
    ("upstream_statuses", "max_attempts"),
    [((503, 429), 3), ((500, 599), 2), ((400,), 3)],
    ids=["429-stops", "attempts-exhausted", "400-stops"],
)
async def test_http_retry_stops_at_non_retryable_status_or_attempt_limit(
    session_factory: async_sessionmaker[AsyncSession],
    run: AiRun,
    monkeypatch: pytest.MonkeyPatch,
    upstream_statuses: tuple[int, ...],
    max_attempts: int,
) -> None:
    """只重试 5xx，遇到其他状态或达到次数上限时返回最后一次错误。"""
    monkeypatch.setattr(settings, "model_max_attempts", max_attempts)
    remaining_statuses = iter(upstream_statuses)
    seen_statuses: list[int] = []

    def respond(request: httpx.Request) -> httpx.Response:
        status_code = next(remaining_statuses)
        seen_statuses.append(status_code)
        return error_response(status_code)

    async with fake_upstream(respond) as client:
        with pytest.raises(APIStatusError) as exc:
            await send(session_factory, run, client)

    assert exc.value.status_code == upstream_statuses[-1]
    assert tuple(seen_statuses) == upstream_statuses
    calls = await calls_of(session_factory, run)
    assert len(calls) == len(upstream_statuses)
    assert all(call.outcome == "http_error" for call in calls)


@pytest.mark.usefixtures("no_retry_delay")
@pytest.mark.parametrize(
    "transport_error",
    [httpx.ReadTimeout, httpx.ConnectError],
    ids=["timeout", "connection-error"],
)
async def test_transport_error_retries_and_returns_success(
    session_factory: async_sessionmaker[AsyncSession],
    run: AiRun,
    monkeypatch: pytest.MonkeyPatch,
    transport_error: type[httpx.TransportError],
) -> None:
    """网络失败后重新发送，失败用量未知，成功用量正常入账。"""
    monkeypatch.setattr(settings, "model_max_attempts", 2)
    sends = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal sends
        sends += 1
        if sends == 1:
            raise transport_error("test transport failure", request=request)
        return completion_response(response_id="retry-success")

    async with fake_upstream(respond) as client:
        response = await send(session_factory, run, client)

    assert response.id == "retry-success"
    assert sends == 2
    calls = await calls_of(session_factory, run)
    assert len(calls) == 2
    assert outcomes_and_usage(calls) == {("unknown", None, None), ("success", 12, 3)}


# ---------- JSON 修复：校验失败后带错误类型重发一次 ----------


async def test_invalid_json_output_is_repaired_and_accounted_for(
    session_factory: async_sessionmaker[AsyncSession],
    run: AiRun,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """字段类型出错时附带校验信息再请求，失败和成功的用量分别保留。"""

    class ParsedJob(BaseModel):
        requirements: list[str]

    def validate(response: ChatCompletion) -> None:
        ParsedJob.model_validate_json(response.choices[0].message.content or "")

    # 次数上限设为 1：修复重发不占重试次数，仍然能发出第二次
    monkeypatch.setattr(settings, "model_max_attempts", 1)
    monkeypatch.setattr(settings, "parse_jd", ModelSettings(max_tokens=64))
    messages: list[ChatCompletionMessageParam] = [
        {
            "role": "user",
            "content": "岗位要求 Python。请返回 JSON，requirements 字段为字符串列表。",
        },
    ]
    budget = ModelBudget(remaining_calls=2, remaining_tokens=4096)
    sent_messages: list[list[ChatCompletionMessageParam]] = []
    responses = iter(
        [
            completion_response('{"requirements": "Python"}', response_id="repair-1"),
            completion_response(
                '{"requirements": ["Python"]}',
                prompt_tokens=26,
                completion_tokens=5,
                response_id="repair-2",
            ),
        ]
    )

    def respond(request: httpx.Request) -> httpx.Response:
        sent_messages.append(loads(request.content)["messages"])
        return next(responses)

    async with fake_upstream(respond) as client:
        response = await send(
            session_factory,
            run,
            client,
            purpose="parse_jd",
            messages=messages,
            json_output=True,
            budget=budget,
            validate=validate,
        )

    assert response.id == "repair-2"
    first_messages, retry_messages = sent_messages
    assert len(messages) == 1  # 网关没有改动调用方传入的列表
    assert first_messages == retry_messages[:-1] == messages
    assert "list_type" in retry_messages[-1]["content"]
    assert budget.remaining_calls == 0
    calls = await calls_of(session_factory, run)
    assert outcomes_and_usage(calls) == {("invalid_output", 12, 3), ("success", 26, 5)}
