from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from app.config import settings
from app.database import (
    create_connection,
    initialize_schema,
    insert_user_message,
    insert_assistant_message,
    load_recent_messages,
    upsert_conversation,
)
from app.schemas import ChatRequest, ChatResponse, HealthResponse
from app.services.llm import (
    LLMConnectionError,
    LLMTimeoutError,
    LLMUpstreamError,
    LLMResponseError,
    generate_reply,
)


app = FastAPI(title=settings.app_name)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if request.conversation_id == "closed-001":
        raise HTTPException(
            status_code=409,
            detail="Conversation is closed.",
        )
    connection = create_connection(settings.database_path)

    try:
        initialize_schema(connection)
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
        insert_user_message(
            connection=connection,
            conversation_id=request.conversation_id,
            content=request.message,
            created_at=timestamp,
        )
        connection.commit()
    finally:
        connection.close()

    try:
        result = await generate_reply(
            message=request.message,
            history=history,
        )
    except LLMTimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=str(exc),
        ) from exc
    except LLMConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except LLMUpstreamError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
    except LLMResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    response_timestamp = datetime.now(timezone.utc).isoformat()
    connection = create_connection(settings.database_path)

    try:
        insert_assistant_message(
            connection=connection,
            conversation_id=request.conversation_id,
            content=result.answer,
            created_at=response_timestamp,
        )
        connection.commit()
    finally:
        connection.close()

    return ChatResponse(
        conversation_id=request.conversation_id,
        answer=result.answer,
    )
