"""用模拟 HTTP 响应和独立数据库连接验证每次模型尝试的持久化边界。"""

from json import loads
from unittest.mock import Mock
from uuid import UUID, uuid4

import httpx
import pytest
from openai import APIStatusError, APITimeoutError, AsyncOpenAI
from openai.types.chat import ChatCompletion
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobpilot.config import ModelPurpose, ModelSettings, settings
from jobpilot.db.models import AiRun, ModelCall, User
from jobpilot.services.llm_gateway import request_completion


@pytest.mark.parametrize(
    ("thinking", "json_output"),
    [(False, True), (True, False)],
    ids=["json-output", "thinking"],
)
async def test_each_request_has_a_durable_call(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    thinking: bool,
    json_output: bool,
) -> None:
    """发送时就能看到登记；成功、校验失败、超时及 HTTP 错误逐笔结算。"""
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
    async with session_factory.begin() as session:
        owner = User(email="ledger@example.invalid", hashed_password="test")
        session.add(owner)
        await session.flush()
        run = AiRun(user_id=owner.user_id, kind="tailor")
        session.add(run)
    seen_ids: list[UUID] = []

    async def respond(request: httpx.Request) -> httpx.Response:
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

        async with session_factory() as reader:
            records = (await reader.scalars(select(ModelCall))).all()
            (current,) = [row for row in records if row.call_id not in seen_ids]
            assert current.run_id == run.run_id and current.user_id == owner.user_id
            assert current.purpose == "rewrite" and current.model == body["model"]
            assert current.outcome == "unknown" and current.latency_ms is None
            assert current.prompt_tokens is None and current.completion_tokens is None
            seen_ids.append(current.call_id)
        if len(seen_ids) == 3:
            raise httpx.ReadTimeout("test timeout", request=request)
        if len(seen_ids) == 4:
            return httpx.Response(503, json={"error": {"message": "test unavailable"}})
        return httpx.Response(
            200,
            json={
                "id": "test",
                "object": "chat.completion",
                "created": 0,
                "model": body["model"],
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "test result"},
                    }
                ],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 3,
                    "total_tokens": 15,
                },
            },
        )

    def reject_output(response: ChatCompletion) -> None:
        raise ValueError("invalid model output")

    async with AsyncOpenAI(
        api_key="test",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
    ) as client:

        async def send(*, invalid: bool = False) -> ChatCompletion:
            return await request_completion(
                session_factory,
                owner.user_id,
                run.run_id,
                client=client,
                purpose="rewrite",
                messages=[{"role": "user", "content": "test"}],
                json_output=json_output,
                validate=reject_output if invalid else None,
            )

        async with session_factory() as business:
            business.add(User(email="rollback@example.invalid", hashed_password="test"))
            await business.flush()
            response = await send()
            assert response.choices[0].message.content == "test result"
            with pytest.raises(ValueError, match="invalid model output"):
                await send(invalid=True)
            with pytest.raises(APITimeoutError):
                await send()
            with pytest.raises(APIStatusError):
                await send()
            await business.rollback()

    async with session_factory() as reader:
        rows = {
            row.call_id: row for row in (await reader.scalars(select(ModelCall))).all()
        }
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
            assert (
                rows[key].prompt_tokens is None and rows[key].completion_tokens is None
            )
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
        )

    session_factory.begin.assert_not_called()
    client.with_options.assert_not_called()


@pytest.mark.parametrize("purpose", list(ModelPurpose))
def test_every_purpose_has_model_settings(purpose: ModelPurpose) -> None:
    """新增用途却漏加配置字段时，在测试阶段而不是首次调用时暴露。"""
    assert isinstance(settings.model_for_purpose(purpose), ModelSettings)
