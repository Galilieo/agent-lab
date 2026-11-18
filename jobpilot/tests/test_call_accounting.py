"""用模拟 HTTP 响应和独立数据库连接验证每次模型尝试的持久化边界。"""

from uuid import UUID

import httpx
import pytest
from openai import APIStatusError, APITimeoutError, AsyncOpenAI
from openai.types.chat import ChatCompletion
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobpilot.db.models import AiRun, ModelCall, User
from jobpilot.services.llm_gateway import request_completion


async def test_each_request_has_a_durable_call(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """发送时就能看到登记；成功、校验失败、超时及 HTTP 错误逐笔结算。"""
    async with session_factory.begin() as session:
        owner = User(email="ledger@example.invalid", hashed_password="test")
        session.add(owner)
        await session.flush()
        run = AiRun(user_id=owner.user_id, kind="tailor")
        session.add(run)
    seen_ids: list[UUID] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        async with session_factory() as reader:
            records = (await reader.scalars(select(ModelCall))).all()
            (current,) = [row for row in records if row.call_id not in seen_ids]
            assert current.run_id == run.run_id and current.user_id == owner.user_id
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
                "model": "test",
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
                model="test",
                messages=[{"role": "user", "content": "test"}],
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
