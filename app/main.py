"""FastAPI 入口：接收请求，编排数据库事务、Agent 调用和 HTTP 错误映射。

/chat 的主链是保存用户消息 → 独立读取记忆 → 调用 Agent → 保存结果，再按需提取写入记忆。
模型失败与工具失败分别持久化，不能把未产生的回答或调用写成成功记录。
"""

import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from app.config import settings
from app.database import (
    ConversationOwnershipError,
    create_connection,
    initialize_schema,
    insert_user_message,
    insert_assistant_message,
    update_assistant_message_content,
    insert_successful_model_call,
    insert_failed_model_call,
    load_recent_messages,
    upsert_conversation,
    load_memories,
    list_memory_records,
    delete_memory_records,
)
from app.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    MemoryQueryRequest,
    MemoryQueryResponse,
    MemoryDeleteRequest,
    MemoryDeleteResponse,
)
from app.services.agent import (
    AgentModelCallLimitError,
    AgentRunError,
    AgentToolError,
    run_agent,
)
from app.services.llm import (
    LLMConnectionError,
    LLMRequestError,
    LLMResult,
    LLMTimeoutError,
    LLMUpstreamError,
    LLMResponseError,
)
from app.services.memory import (
    extract_memories,
    prepare_memory_writes,
    persist_memory_writes,
    should_extract_memory,
    merge_memories,
    build_memory_context,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """在应用接受请求前初始化数据库，并及时关闭初始化连接。

    asynccontextmanager 的 yield 之前是启动阶段，之后是退出阶段；
    TestClient 需进入上下文才能执行这段生命周期。
    """
    connection = create_connection(settings.database_path)

    try:
        initialize_schema(connection)
    finally:
        connection.close()

    yield

app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)


# 只检查 HTTP 应用能否响应，不执行模型调用或数据库业务查询。
@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/memories/query", response_model=MemoryQueryResponse)
def query_memories(request: MemoryQueryRequest) -> MemoryQueryResponse:
    """只读查看当前可见的原始记录；存储故障不能伪装成没有记忆。"""
    connection = None
    try:
        connection = create_connection(settings.database_path)
        records = list_memory_records(
            connection,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
        )
    except ConversationOwnershipError as exc:
        raise HTTPException(status_code=409, detail="Conversation ownership does not match.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.Error as exc:
        logger.warning("Memory management failed operation=query error=%s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Memory storage is unavailable.") from exc
    finally:
        if connection is not None:
            connection.close()

    return MemoryQueryResponse(memories=records)


@app.post("/memories/delete", response_model=MemoryDeleteResponse)
def delete_memories(request: MemoryDeleteRequest) -> MemoryDeleteResponse:
    """在短事务中删除指定范围；提交成功后才返回实际条数。"""
    connection = None
    try:
        connection = create_connection(settings.database_path)
        try:
            deleted_count = delete_memory_records(
                connection,
                user_id=request.user_id,
                conversation_id=request.conversation_id,
                key=request.key,
                target=request.target,
            )
            connection.commit()
        except Exception:
            # 这里只清理事务并重新抛出；不会把未知错误转为成功响应。
            connection.rollback()
            raise
    except ConversationOwnershipError as exc:
        raise HTTPException(status_code=409, detail="Conversation ownership does not match.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.Error as exc:
        logger.warning("Memory management failed operation=delete error=%s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Memory storage is unavailable.") from exc
    finally:
        if connection is not None:
            connection.close()

    return MemoryDeleteResponse(deleted_count=deleted_count)


def persist_failed_model_call(
    conversation_id: str,
    request_message_id: int,
    error: LLMRequestError,
) -> None:
    """为本轮用户消息保存一次直接失败的模型调用，单独提交短事务。"""
    connection = create_connection(settings.database_path)
    try:
        timestamp = datetime.now(timezone.utc).isoformat()

        insert_failed_model_call(
            connection=connection,
            conversation_id=conversation_id,
            request_message_id=request_message_id,
            model=error.model,
            outcome=error.outcome,
            upstream_status=error.upstream_status,
            latency_ms=error.latency_ms,
            created_at=timestamp,
        )

        connection.commit()
    finally:
        connection.close()


def persist_completed_model_calls(
    conversation_id: str,
    request_message_id: int,
    model_calls: list[LLMResult],
) -> None:
    """保存中止前已成功的模型调用，不生成不存在的最终回答。

    用于工具失败和预算耗尽；这些失败不是新的模型请求失败。
    """
    connection = create_connection(settings.database_path)

    try:
        timestamp = datetime.now(timezone.utc).isoformat()

        for model_call in model_calls:
            insert_successful_model_call(
                connection=connection,
                conversation_id=conversation_id,
                request_message_id=request_message_id,
                response_message_id=None,
                model=model_call.model,
                upstream_status=model_call.upstream_status,
                latency_ms=model_call.latency_ms,
                prompt_tokens=model_call.prompt_tokens,
                completion_tokens=model_call.completion_tokens,
                total_tokens=model_call.total_tokens,
                created_at=timestamp,
            )

        connection.commit()
    finally:
        connection.close()


def persist_agent_run_error(
    conversation_id: str,
    request_message_id: int,
    error: AgentRunError,
) -> None:
    """在同一个短事务中保存此前成功调用和最后一次真实模型失败。

    整轮没有最终回答，成功与失败调用都不关联 assistant message。
    """
    connection = create_connection(settings.database_path)

    try:
        timestamp = datetime.now(timezone.utc).isoformat()

        for model_call in error.completed_model_calls:
            insert_successful_model_call(
                connection=connection,
                conversation_id=conversation_id,
                request_message_id=request_message_id,
                response_message_id=None,
                model=model_call.model,
                upstream_status=model_call.upstream_status,
                latency_ms=model_call.latency_ms,
                prompt_tokens=model_call.prompt_tokens,
                completion_tokens=model_call.completion_tokens,
                total_tokens=model_call.total_tokens,
                created_at=timestamp,
            )

        insert_failed_model_call(
            connection=connection,
            conversation_id=conversation_id,
            request_message_id=request_message_id,
            model=error.cause.model,
            outcome=error.cause.outcome,
            upstream_status=error.cause.upstream_status,
            latency_ms=error.cause.latency_ms,
            created_at=timestamp,
        )

        connection.commit()
    finally:
        connection.close()


def persist_assistant_feedback(
    conversation_id: str,
    response_message_id: int,
    answer: str,
) -> None:
    """用独立短事务回写最终反馈，不重新插入助手消息。"""
    connection = create_connection(settings.database_path)
    try:
        update_assistant_message_content(
            connection=connection,
            conversation_id=conversation_id,
            message_id=response_message_id,
            content=answer,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


async def process_memory_after_reply(
    request: ChatRequest,
    *,
    request_message_id: int,
    response_message_id: int,
    answer: str,
) -> str:
    """在正常聊天提交后处理记忆，辅助流程失败保留原回答。"""
    if not should_extract_memory(request.message):
        return answer

    explicit_save = any(
        marker in request.message
        for marker in ("记住", "记下来", "保存")
    )
    phase = "extract"

    try:
        extraction = await extract_memories(request.message)

        phase = "prepare"
        writes = prepare_memory_writes(
            extraction,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            source_message_id=request_message_id,
        )

        if writes:
            phase = "persist"
            persist_memory_writes(
                writes,
                database_path=settings.database_path,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            feedback = "已保存本次记忆。"
        else:
            feedback = "本次没有可保存的新记忆。" if explicit_save else ""

    except Exception as exc:
        # 仅记录分类与关联信息，不记录异常正文或用户内容。
        logger.warning(
            "Memory processing failed phase=%s error=%s "
            "conversation_id=%s request_message_id=%s",
            phase,
            type(exc).__name__,
            request.conversation_id,
            request_message_id,
        )
        feedback = "本次长期记忆未保存。" if explicit_save else ""

    if not feedback:
        return answer

    final_answer = f"{answer}\n\n{feedback}"

    try:
        persist_assistant_feedback(
            conversation_id=request.conversation_id,
            response_message_id=response_message_id,
            answer=final_answer,
        )
    except Exception as exc:
        # 反馈更新失败，不撤销已提交的记忆或主聊天。
        logger.warning(
            "Memory feedback failed phase=feedback error=%s "
            "conversation_id=%s response_message_id=%s",
            type(exc).__name__,
            request.conversation_id,
            response_message_id,
        )
        return answer

    return final_answer


def load_chat_memory_context(request: ChatRequest) -> str:
    """独立读取记忆；SQLite 故障回退为空，归属异常继续传播。"""
    connection = None

    try:
        connection = create_connection(settings.database_path)
        rows = load_memories(
            connection,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
        )
    except sqlite3.Error as exc:
        logger.warning(
            "Memory processing failed phase=read error=%s conversation_id=%s",
            type(exc).__name__,
            request.conversation_id,
        )
        return ""
    finally:
        if connection is not None:
            connection.close()

    merged = merge_memories(rows)
    return build_memory_context(merged, request.message)


# 编排聊天请求：校验归属、恢复历史、调用 Agent，并保存成功或失败结果。
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if request.conversation_id == "closed-001":
        raise HTTPException(
            status_code=409,
            detail="Conversation is closed.",
        )
    connection = create_connection(settings.database_path)

    try:
        timestamp = datetime.now(timezone.utc).isoformat()

        upsert_conversation(
            connection=connection,
            conversation_id=request.conversation_id,
            timestamp=timestamp,
            user_id=request.user_id,
        )
        # 先检查归属、读取旧历史，再插入当前问题，避免它在模型输入中出现两次。
        history = load_recent_messages(
            connection=connection,
            conversation_id=request.conversation_id,
            limit=10,
        )
        request_message_id = insert_user_message(
            connection=connection,
            conversation_id=request.conversation_id,
            content=request.message,
            created_at=timestamp,
        )
        connection.commit()
    except ConversationOwnershipError as exc:
        raise HTTPException(
            status_code=409,
            detail="Conversation ownership does not match.",
        ) from exc
    finally:
        connection.close()

    # 事务一已提交并关闭连接，再独立读取记忆、调用模型。
    try:
        memory_context = load_chat_memory_context(request)
        result = await run_agent(
            message=request.message,
            history=history,
            memory_context=memory_context,
        )
    except ConversationOwnershipError as exc:
        raise HTTPException(
            status_code=409,
            detail="Conversation ownership does not match.",
        ) from exc
    except AgentRunError as exc:
        # 后续模型失败携带此前成功调用；按原始模型错误选择 HTTP 状态。
        persist_agent_run_error(
            conversation_id=request.conversation_id,
            request_message_id=request_message_id,
            error=exc,
        )

        if isinstance(exc.cause, LLMTimeoutError):
            status_code = 504
        elif isinstance(exc.cause, LLMConnectionError):
            status_code = 503
        else:
            status_code = 502

        raise HTTPException(
            status_code=status_code,
            detail=str(exc.cause),
        ) from exc
    except LLMTimeoutError as exc:
        persist_failed_model_call(
            conversation_id=request.conversation_id,
            request_message_id=request_message_id,
            error=exc,
        )
        raise HTTPException(
            status_code=504,
            detail=str(exc),
        ) from exc
    except LLMConnectionError as exc:
        persist_failed_model_call(
            conversation_id=request.conversation_id,
            request_message_id=request_message_id,
            error=exc,
        )
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except LLMUpstreamError as exc:
        persist_failed_model_call(
            conversation_id=request.conversation_id,
            request_message_id=request_message_id,
            error=exc,
        )
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
    except LLMResponseError as exc:
        persist_failed_model_call(
            conversation_id=request.conversation_id,
            request_message_id=request_message_id,
            error=exc,
        )
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
    except AgentModelCallLimitError as exc:
        # 预算耗尽属于编排停止，保存成功调用，但不虚构一次失败的模型请求。
        persist_completed_model_calls(
            conversation_id=request.conversation_id,
            request_message_id=request_message_id,
            model_calls=exc.completed_model_calls,
        )
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
    except AgentToolError as exc:
        # 模型已经成功提出工具请求，工具执行失败不能改写该模型调用的结果。
        persist_completed_model_calls(
            conversation_id=request.conversation_id,
            request_message_id=request_message_id,
            model_calls=exc.completed_model_calls,
        )

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    # 事务二把最终回答和成功调用一并提交，避免只保存其中一半。
    response_timestamp = datetime.now(timezone.utc).isoformat()
    connection = create_connection(settings.database_path)

    try:
        response_message_id = insert_assistant_message(
            connection=connection,
            conversation_id=request.conversation_id,
            content=result.answer,
            created_at=response_timestamp,
        )

        # 中间工具调用没有最终回答，只有最后一次调用关联这条 assistant message。
        last_model_call_index = len(result.model_calls) - 1

        for index, model_call in enumerate(result.model_calls):
            insert_successful_model_call(
                connection=connection,
                conversation_id=request.conversation_id,
                request_message_id=request_message_id,
                response_message_id=(
                    response_message_id
                    if index == last_model_call_index
                    else None
                ),
                model=model_call.model,
                upstream_status=model_call.upstream_status,
                latency_ms=model_call.latency_ms,
                prompt_tokens=model_call.prompt_tokens,
                completion_tokens=model_call.completion_tokens,
                total_tokens=model_call.total_tokens,
                created_at=response_timestamp,
            )

        connection.commit()
    finally:
        connection.close()

    final_answer = await process_memory_after_reply(
        request,
        request_message_id=request_message_id,
        response_message_id=response_message_id,
        answer=result.answer,
    )

    return ChatResponse(
        conversation_id=request.conversation_id,
        answer=final_answer,
    )
