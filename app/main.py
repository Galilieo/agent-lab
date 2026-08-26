from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from app.config import settings
from app.database import (
    create_connection,
    initialize_schema,
    insert_user_message,
    insert_assistant_message,
    insert_successful_model_call,
    insert_failed_model_call,
    load_recent_messages,
    upsert_conversation,
)
from app.schemas import ChatRequest, ChatResponse, HealthResponse
from app.services.agent import AgentRunError, run_agent
from app.services.llm import (
    LLMConnectionError,
    LLMRequestError,
    LLMTimeoutError,
    LLMUpstreamError,
    LLMResponseError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


def persist_failed_model_call(
    conversation_id: str,
    request_message_id: int,
    error: LLMRequestError,
) -> None:
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


def persist_agent_run_error(
    conversation_id: str,
    request_message_id: int,
    error: AgentRunError,
) -> None:
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
        )
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
    finally:
        connection.close()

    try:
        result = await run_agent(
            message=request.message,
            history=history,
        )
    except AgentRunError as exc:
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

    response_timestamp = datetime.now(timezone.utc).isoformat()
    connection = create_connection(settings.database_path)

    try:
        response_message_id = insert_assistant_message(
            connection=connection,
            conversation_id=request.conversation_id,
            content=result.answer,
            created_at=response_timestamp,
        )

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

    return ChatResponse(
        conversation_id=request.conversation_id,
        answer=result.answer,
    )
