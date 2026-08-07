from fastapi import FastAPI, HTTPException

from app.config import settings
from app.schemas import ChatRequest, ChatResponse, HealthResponse
from app.services.llm import generate_reply


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

    answer = await generate_reply(request.message)
    return ChatResponse(
        conversation_id=request.conversation_id,
        answer=answer,
    )
